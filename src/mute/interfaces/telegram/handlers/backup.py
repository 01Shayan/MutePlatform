"""Backup Telegram interface — a pure interface over :class:`BackupApplicationService`.

This handler mirrors the CLI Backup workflow (menu → create/history/delete) without
duplicating any business logic or touching the filesystem. Every screen edits the same
Telegram message; the only new message ever sent is the backup archive itself, delivered as a
document when the user chooses Download Backup.
"""

from __future__ import annotations

import asyncio
import io

from telegram import InputFile, Update
from telegram.error import BadRequest
from telegram.ext import ContextTypes

from ....core.logging import get_logger, use_workspace
from ....core.workspace import Workspace
from ....services.backup import BackupApplicationService, BackupOperationError
from ....services.workspace import ConnectionStatus, WorkspaceApplicationService
from ..auth import OwnerAuthorization
from ..keyboards import (
    backup_back_keyboard,
    backup_history_keyboard,
    backup_menu_keyboard,
    backup_result_keyboard,
    dashboard_keyboard,
    delete_all_confirm_keyboard,
    delete_menu_keyboard,
    delete_single_confirm_keyboard,
    delete_single_list_keyboard,
)
from ..messages import (
    backup_error,
    backup_history,
    backup_progress,
    backup_result,
    backup_status,
    dashboard,
    delete_all_confirmation,
    delete_menu,
    delete_single_confirmation,
    no_backups_to_delete,
)
from ..router import Router

logger = get_logger("telegram")


def make_backup_handler(
    authorization: OwnerAuthorization,
    router: Router,
    workspaces_service: WorkspaceApplicationService,
):
    """Build the callback handler for every ``backup:*`` action."""

    async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not authorization.allows_update(update) or update.callback_query is None:
            return
        query = update.callback_query
        chat = update.effective_chat
        if chat is None:
            return

        workspace = _resolve_workspace(router, workspaces_service, chat.id)
        if workspace is None:
            await query.answer("Workspace is no longer available.", show_alert=True)
            return

        service = BackupApplicationService()
        data = query.data or ""

        if data == "backup:menu":
            await query.answer()
            router.backup(chat.id)
            await _show_menu(query, service, workspace)
        elif data == "backup:dashboard":
            await query.answer()
            router.dashboard(chat.id, workspace.name)
            item = workspaces_service.navigation_item(workspace.name)
            await _safe_edit(query, dashboard(item), dashboard_keyboard())
        elif data == "backup:create":
            await _create_export(update, context, router, service, workspace)
        elif data == "backup:history":
            await query.answer()
            router.backup_history(chat.id)
            await _safe_edit(query, backup_history(service.archives(workspace)), backup_history_keyboard())
        elif data == "backup:delete":
            await query.answer()
            router.backup_delete(chat.id)
            await _safe_edit(query, delete_menu(), delete_menu_keyboard())
        elif data == "backup:delete-single":
            await query.answer()
            await _show_delete_single(query, router, service, workspace, chat.id)
        elif data == "backup:delete-all":
            await query.answer()
            await _show_delete_all(query, router, service, workspace, chat.id)
        elif data.startswith("backup:delete:"):
            await query.answer()
            await _confirm_delete_single(query, router, service, workspace, chat.id, data.removeprefix("backup:delete:"))
        elif data.startswith("backup:confirm-delete:"):
            await query.answer()
            await _perform_delete_single(query, router, service, workspace, chat.id, data.removeprefix("backup:confirm-delete:"))
        elif data == "backup:confirm-delete-all":
            await query.answer()
            service.delete_all_archives(workspace)
            router.backup(chat.id)
            await _show_menu(query, service, workspace)
        elif data.startswith("backup:download:"):
            await _download(update, context, service, workspace, chat.id, data.removeprefix("backup:download:"))

    return handle


def _resolve_workspace(
    router: Router, workspaces_service: WorkspaceApplicationService, chat_id: int
) -> Workspace | None:
    name = router.session(chat_id).current_workspace
    if not name:
        return None
    workspace = workspaces_service.workspace(name)
    if workspace is not None:
        # Route logging into the active workspace, exactly as the CLI does when opening one, so
        # Telegram-triggered application, backup, and error logs land in workspaces/<name>/logs/.
        use_workspace(workspace.logs_dir)
    return workspace


async def _show_menu(query, service: BackupApplicationService, workspace: Workspace) -> None:
    latest = service.latest(workspace)
    await _safe_edit(query, backup_status(latest, workspace=workspace.name), backup_menu_keyboard())


async def _show_delete_single(query, router: Router, service, workspace, chat_id) -> None:
    archives = service.archives(workspace)
    if not archives:
        router.backup_delete(chat_id)
        await _safe_edit(query, no_backups_to_delete(), delete_menu_keyboard())
        return
    router.backup_delete_single(chat_id)
    names = [archive.path.name for archive in archives]
    await _safe_edit(query, backup_history(archives, title="Delete Single Backup"), delete_single_list_keyboard(names))


async def _show_delete_all(query, router: Router, service, workspace, chat_id) -> None:
    if not service.archives(workspace) and service.latest(workspace) is None:
        router.backup_delete(chat_id)
        await _safe_edit(query, no_backups_to_delete(), delete_menu_keyboard())
        return
    router.backup_delete_all_confirmation(chat_id)
    await _safe_edit(query, delete_all_confirmation(workspace.name), delete_all_confirm_keyboard())


async def _confirm_delete_single(query, router: Router, service, workspace, chat_id, archive_name) -> None:
    archive = _find_archive(service, workspace, archive_name)
    if archive is None:
        router.backup(chat_id)
        await _show_menu(query, service, workspace)
        return
    router.backup_delete_confirmation(chat_id, archive_name)
    await _safe_edit(
        query,
        delete_single_confirmation(workspace.name, archive),
        delete_single_confirm_keyboard(archive_name),
    )


async def _perform_delete_single(query, router: Router, service, workspace, chat_id, archive_name) -> None:
    archive = _find_archive(service, workspace, archive_name)
    if archive is not None:
        service.delete_archive(workspace, archive)
    router.backup(chat_id)
    await _show_menu(query, service, workspace)


async def _create_export(update, context, router: Router, service, workspace) -> None:
    query = update.callback_query
    chat_id = update.effective_chat.id
    message_id = query.message.message_id
    router.backup(chat_id)
    router.remember_message(chat_id, message_id)

    await query.answer()
    await _safe_edit_message(context, chat_id, message_id, backup_progress("Connecting…"))

    loop = asyncio.get_running_loop()
    bridge = _ProgressBridge(loop, context.bot, chat_id, message_id)
    try:
        summary = await asyncio.to_thread(service.create_export, workspace, bridge)
    except BackupOperationError as exc:
        WorkspaceApplicationService.record_connection_status(workspace, ConnectionStatus.OFFLINE)
        await _safe_edit_message(context, chat_id, message_id, backup_error(str(exc)), backup_back_keyboard())
        return
    except Exception:  # noqa: BLE001 — surface a friendly message, log the detail
        logger.exception("Unexpected error during Telegram backup export")
        WorkspaceApplicationService.record_connection_status(workspace, ConnectionStatus.OFFLINE)
        await _safe_edit_message(context, chat_id, message_id, backup_error(), backup_back_keyboard())
        return

    WorkspaceApplicationService.record_connection_status(workspace, ConnectionStatus.CONNECTED)
    await _safe_edit_message(
        context, chat_id, message_id, backup_result(summary), backup_result_keyboard(summary.archive_name)
    )


async def _download(update, context, service, workspace, chat_id, archive_name) -> None:
    query = update.callback_query
    download = service.download_archive(workspace, archive_name)
    if download is None:
        await query.answer("This backup no longer exists.", show_alert=True)
        return
    await query.answer()
    await context.bot.send_document(
        chat_id=chat_id,
        document=InputFile(io.BytesIO(download.content), filename=download.filename),
    )
    await _safe_edit(query, backup_status(service.latest(workspace), workspace=workspace.name), backup_menu_keyboard())


def _find_archive(service: BackupApplicationService, workspace: Workspace, archive_name: str):
    return next((item for item in service.archives(workspace) if item.path.name == archive_name), None)


class _ProgressBridge:
    """Maps the sync backup progress callback onto stage edits of one Telegram message.

    The backup runs in a worker thread, so each stage edit is scheduled back onto the bot's
    event loop. Consecutive identical stages are suppressed to avoid redundant edits.
    """

    def __init__(self, loop, bot, chat_id: int, message_id: int) -> None:
        self._loop = loop
        self._bot = bot
        self._chat_id = chat_id
        self._message_id = message_id
        self._last_stage: str | None = None

    def __call__(self, message: str, completed: int, total: int) -> None:
        stage = "Writing backup…" if total and completed >= total else "Loading users…"
        if stage == self._last_stage:
            return
        self._last_stage = stage
        coroutine = self._bot.edit_message_text(
            chat_id=self._chat_id, message_id=self._message_id, text=backup_progress(stage)
        )
        future = asyncio.run_coroutine_threadsafe(coroutine, self._loop)
        try:
            future.result(timeout=10)
        except Exception:  # noqa: BLE001 — progress is best-effort and must not fail the export
            pass


async def _safe_edit(query, text: str, reply_markup=None) -> None:
    try:
        await query.edit_message_text(text, reply_markup=reply_markup)
    except BadRequest as exc:
        if "not modified" not in str(exc).lower():
            raise


async def _safe_edit_message(context, chat_id: int, message_id: int, text: str, reply_markup=None) -> None:
    try:
        await context.bot.edit_message_text(
            chat_id=chat_id, message_id=message_id, text=text, reply_markup=reply_markup
        )
    except BadRequest as exc:
        if "not modified" not in str(exc).lower():
            raise
