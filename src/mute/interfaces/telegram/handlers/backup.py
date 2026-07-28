"""Backup Telegram interface — mirrors CLI Backup (create / auto / max / history / delete).

Manual and Auto Backup both call :meth:`BackupApplicationService.create_export`
(create + retention). After a successful create, the archive is sent to Telegram.
"""

from __future__ import annotations

import asyncio
import io

from telegram import InputFile, Update
from telegram.error import BadRequest
from telegram.ext import ContextTypes

from ....core.logging import get_logger, use_workspace
from ....core.workspace import Workspace
from ....services.backup import (
    BackupApplicationService,
    BackupOperationError,
    parse_auto_backup_interval,
    parse_max_backups,
)
from ....services.workspace import ConnectionStatus, WorkspaceApplicationService
from ....ui.copy import (
    MSG_BACKUP_LOADING_USERS,
    MSG_BACKUP_WRITING,
    MSG_INVALID_INTERVAL,
    MSG_INVALID_MAX_BACKUPS,
)
from ..auth import OwnerAuthorization
from ..conversation import begin_temporary, cleanup_temporary, track_temporary
from ..keyboards import (
    archive_details_keyboard,
    auto_backup_keyboard,
    backup_back_keyboard,
    backup_history_keyboard,
    backup_menu_keyboard,
    backup_result_keyboard,
    cancel_keyboard,
    dashboard_keyboard,
    delete_all_confirm_keyboard,
    delete_menu_keyboard,
    delete_single_confirm_keyboard,
    delete_single_list_keyboard,
    max_backups_keyboard,
)
from ..messages import (
    archive_details,
    ask_backup_interval,
    ask_max_backups,
    auto_backup_status,
    backup_error,
    backup_history,
    backup_progress,
    backup_result,
    backup_status,
    dashboard,
    delete_all_confirmation,
    delete_menu,
    delete_single_confirmation,
    max_backups_status,
    no_backups_to_delete,
)
from ..router import Router
from ..session import Screen

logger = get_logger("telegram")

_TEXT_SCREENS = {Screen.BACKUP_AUTO_INTERVAL, Screen.BACKUP_MAX_INPUT}


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
            await cleanup_temporary(context.bot, router, chat.id)
            router.backup(chat.id)
            await _show_menu(query, service, workspace)
        elif data == "backup:dashboard":
            await query.answer()
            await cleanup_temporary(context.bot, router, chat.id)
            router.dashboard(chat.id, workspace.name)
            item = workspaces_service.navigation_item(workspace.name)
            await _safe_edit(query, dashboard(item), dashboard_keyboard())
        elif data == "backup:create":
            await _create_export(update, context, router, service, workspace, authorization)
        elif data == "backup:auto":
            await query.answer()
            await cleanup_temporary(context.bot, router, chat.id)
            router.backup_auto(chat.id)
            await _show_auto(query, workspace)
        elif data == "backup:auto:enable":
            await query.answer()
            begin_temporary(router, chat.id)
            router.backup_auto_interval(chat.id)
            if query.message is not None:
                router.remember_message(chat.id, query.message.message_id)
            router.session(chat.id).draft["auto_enable"] = True
            await _safe_edit(query, ask_backup_interval(), cancel_keyboard("backup:auto"))
        elif data == "backup:auto:interval":
            await query.answer()
            begin_temporary(router, chat.id)
            router.backup_auto_interval(chat.id)
            if query.message is not None:
                router.remember_message(chat.id, query.message.message_id)
            router.session(chat.id).draft["auto_enable"] = False
            await _safe_edit(query, ask_backup_interval(), cancel_keyboard("backup:auto"))
        elif data == "backup:auto:disable":
            await query.answer()
            workspaces_service.save_backup_settings(workspace, auto_backup_enabled=False)
            refreshed = workspaces_service.workspace(workspace.name) or workspace
            router.backup_auto(chat.id)
            await _show_auto(query, refreshed)
        elif data == "backup:max":
            await query.answer()
            await cleanup_temporary(context.bot, router, chat.id)
            router.backup_max(chat.id)
            await _show_max(query, workspace)
        elif data == "backup:max:change":
            await query.answer()
            begin_temporary(router, chat.id)
            router.backup_max_input(chat.id)
            if query.message is not None:
                router.remember_message(chat.id, query.message.message_id)
            await _safe_edit(query, ask_max_backups(), cancel_keyboard("backup:max"))
        elif data == "backup:history":
            await query.answer()
            await cleanup_temporary(context.bot, router, chat.id)
            await _show_history(query, router, service, workspace, chat.id)
        elif data.startswith("backup:archive:"):
            await query.answer()
            await _show_archive_details(
                query, context, router, service, workspace, chat.id, data.removeprefix("backup:archive:")
            )
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
            await _confirm_delete_single(
                query, router, service, workspace, chat.id, data.removeprefix("backup:delete:")
            )
        elif data.startswith("backup:confirm-delete:"):
            await query.answer()
            await _perform_delete_single(
                query, context, router, service, workspace, chat.id, data.removeprefix("backup:confirm-delete:")
            )
        elif data == "backup:confirm-delete-all":
            await query.answer()
            service.delete_all_archives(workspace)
            router.backup(chat.id)
            await _show_menu(query, service, workspace)
        elif data.startswith("backup:download:"):
            await _download(
                update, context, router, service, workspace, chat.id, data.removeprefix("backup:download:")
            )

    return handle


def make_backup_text_handler(
    authorization: OwnerAuthorization,
    router: Router,
    workspaces_service: WorkspaceApplicationService,
):
    async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
        if not authorization.allows_update(update) or update.effective_message is None:
            return False
        chat = update.effective_chat
        if chat is None:
            return False
        session = router.session(chat.id)
        if session.current_screen not in _TEXT_SCREENS:
            return False
        workspace = _resolve_workspace(router, workspaces_service, chat.id)
        if workspace is None:
            return False

        raw = (update.effective_message.text or "").strip()
        track_temporary(router, chat.id, update.effective_message.message_id)

        if session.current_screen is Screen.BACKUP_AUTO_INTERVAL:
            try:
                interval = parse_auto_backup_interval(raw)
            except ValueError:
                sent = await update.effective_message.reply_text(MSG_INVALID_INTERVAL)
                track_temporary(router, chat.id, sent.message_id)
                return True
            enable = bool(session.draft.get("auto_enable", True))
            kwargs = {"auto_backup_interval": interval}
            if enable:
                kwargs["auto_backup_enabled"] = True
            workspaces_service.save_backup_settings(workspace, **kwargs)
            refreshed = workspaces_service.workspace(workspace.name) or workspace
            await cleanup_temporary(context.bot, router, chat.id)
            router.backup_auto(chat.id)
            message_id = session.last_message_id
            await _safe_edit_message(
                context,
                chat.id,
                message_id,
                auto_backup_status(refreshed),
                auto_backup_keyboard(enabled=True),
            )
            return True

        if session.current_screen is Screen.BACKUP_MAX_INPUT:
            try:
                limit = parse_max_backups(raw)
            except ValueError:
                sent = await update.effective_message.reply_text(MSG_INVALID_MAX_BACKUPS)
                track_temporary(router, chat.id, sent.message_id)
                return True
            workspaces_service.save_backup_settings(workspace, max_backups=limit)
            refreshed = workspaces_service.workspace(workspace.name) or workspace
            BackupApplicationService().enforce_retention(refreshed)
            await cleanup_temporary(context.bot, router, chat.id)
            router.backup_max(chat.id)
            message_id = session.last_message_id
            await _safe_edit_message(
                context,
                chat.id,
                message_id,
                max_backups_status(refreshed),
                max_backups_keyboard(),
            )
            return True

        return False

    return handle


def _resolve_workspace(
    router: Router, workspaces_service: WorkspaceApplicationService, chat_id: int
) -> Workspace | None:
    name = router.session(chat_id).current_workspace
    if not name:
        return None
    workspace = workspaces_service.workspace(name)
    if workspace is not None:
        use_workspace(workspace.logs_dir)
    return workspace


async def _show_menu(query, service: BackupApplicationService, workspace: Workspace) -> None:
    latest = service.latest(workspace)
    await _safe_edit(query, backup_status(latest, workspace=workspace.name), backup_menu_keyboard())


async def _show_auto(query, workspace: Workspace) -> None:
    await _safe_edit(
        query,
        auto_backup_status(workspace),
        auto_backup_keyboard(enabled=bool(workspace.auto_backup_enabled)),
    )


async def _show_max(query, workspace: Workspace) -> None:
    await _safe_edit(query, max_backups_status(workspace), max_backups_keyboard())


async def _show_history(query, router: Router, service, workspace, chat_id) -> None:
    archives = service.archives(workspace)
    router.backup_history(chat_id)
    names = [archive.path.name for archive in archives]
    await _safe_edit(query, backup_history(archives, selectable=True), backup_history_keyboard(names))


async def _show_archive_details(query, context, router, service, workspace, chat_id, archive_name) -> None:
    archive = _find_archive(service, workspace, archive_name)
    if archive is None:
        await cleanup_temporary(context.bot, router, chat_id)
        await _show_history(query, router, service, workspace, chat_id)
        return
    begin_temporary(router, chat_id)
    if query.message is not None:
        router.remember_message(chat_id, query.message.message_id)
    router.backup_archive_detail(chat_id, archive_name)
    await _safe_edit(
        query,
        archive_details(workspace.name, archive),
        archive_details_keyboard(archive_name),
    )


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
    session = router.session(chat_id)
    from_details = session.current_screen is Screen.BACKUP_ARCHIVE_DETAIL
    if from_details:
        session.draft["backup_delete_no"] = f"backup:archive:{archive_name}"
        session.draft["backup_delete_return_history"] = True
    else:
        session.draft.pop("backup_delete_no", None)
        session.draft.pop("backup_delete_return_history", None)
    router.backup_delete_confirmation(chat_id, archive_name)
    no_data = session.draft.get("backup_delete_no", "backup:delete-single")
    await _safe_edit(
        query,
        delete_single_confirmation(workspace.name, archive),
        delete_single_confirm_keyboard(archive_name, no_data=no_data),
    )


async def _perform_delete_single(query, context, router, service, workspace, chat_id, archive_name) -> None:
    archive = _find_archive(service, workspace, archive_name)
    if archive is not None:
        service.delete_archive(workspace, archive)
    session = router.session(chat_id)
    return_history = bool(session.draft.pop("backup_delete_return_history", False))
    session.draft.pop("backup_delete_no", None)
    await cleanup_temporary(context.bot, router, chat_id)
    if return_history:
        await _show_history(query, router, service, workspace, chat_id)
        return
    router.backup(chat_id)
    await _show_menu(query, service, workspace)


async def _create_export(update, context, router: Router, service, workspace, authorization) -> None:
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
    await _send_archive_to_owners(context, service, workspace, summary.archive_name, authorization)
    await _safe_edit_message(
        context, chat_id, message_id, backup_result(summary), backup_result_keyboard(summary.archive_name)
    )


async def _send_archive_to_owners(context, service, workspace, archive_name, authorization) -> None:
    download = service.download_archive(workspace, archive_name)
    if download is None:
        return
    for owner_id in authorization.owner_ids:
        try:
            await context.bot.send_document(
                chat_id=owner_id,
                document=InputFile(io.BytesIO(download.content), filename=download.filename),
            )
        except Exception:  # noqa: BLE001 — delivery is best-effort after a successful export
            logger.exception("Could not send backup '%s' to owner %s", archive_name, owner_id)


async def _download(update, context, router, service, workspace, chat_id, archive_name) -> None:
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
    session = router.session(chat_id)
    if session.current_screen is Screen.BACKUP_ARCHIVE_DETAIL:
        archive = _find_archive(service, workspace, archive_name)
        if archive is None:
            await cleanup_temporary(context.bot, router, chat_id)
            await _show_history(query, router, service, workspace, chat_id)
            return
        await _safe_edit(
            query,
            archive_details(workspace.name, archive),
            archive_details_keyboard(archive_name),
        )
        return
    router.backup(chat_id)
    await _safe_edit(query, backup_status(service.latest(workspace), workspace=workspace.name), backup_menu_keyboard())


def _find_archive(service: BackupApplicationService, workspace: Workspace, archive_name: str):
    return next((item for item in service.archives(workspace) if item.path.name == archive_name), None)


class _ProgressBridge:
    """Maps the sync backup progress callback onto stage edits of one Telegram message."""

    def __init__(self, loop, bot, chat_id: int, message_id: int) -> None:
        self._loop = loop
        self._bot = bot
        self._chat_id = chat_id
        self._message_id = message_id
        self._last_stage: str | None = None

    def __call__(self, message: str, completed: int, total: int) -> None:
        stage = MSG_BACKUP_WRITING if total and completed >= total else MSG_BACKUP_LOADING_USERS
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
    if message_id is None:
        return
    try:
        await context.bot.edit_message_text(
            chat_id=chat_id, message_id=message_id, text=text, reply_markup=reply_markup
        )
    except BadRequest as exc:
        if "not modified" not in str(exc).lower():
            raise
