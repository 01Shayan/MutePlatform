"""Bulk Operations / Group Manager Telegram interface."""

from __future__ import annotations

import asyncio

from telegram import Update
from telegram.error import BadRequest
from telegram.ext import ContextTypes

from ....core.logging import get_logger, use_workspace
from ....core.workspace import Workspace
from ....services.bulk_operations.group_manager import (
    GroupManagerApplicationService,
    GroupManagerError,
)
from ....services.bulk_operations.group_manager.checker import parse_group_ids
from ....services.group_checker.models import GroupQueryDescriptor, GroupQueryType
from ....services.workspace import WorkspaceApplicationService
from ..auth import OwnerAuthorization
from ..conversation import begin_temporary, cleanup_temporary, track_temporary
from ..keyboards import (
    bulk_ops_keyboard,
    dashboard_keyboard,
    gm_actions_keyboard,
    gm_backups_keyboard,
    gm_coming_soon_keyboard,
    gm_confirm_keyboard,
    gm_input_keyboard,
    gm_menu_keyboard,
    gm_query_keyboard,
    gm_result_keyboard,
)
from ..messages import (
    bulk_ops_menu,
    dashboard,
    gm_ask_group_ids,
    gm_coming_soon,
    gm_confirmation,
    gm_error,
    gm_invalid_ids,
    gm_menu,
    gm_no_backups,
    gm_progress,
    gm_select_backup,
    gm_select_query,
    gm_working_set,
)
from ..router import Router
from ..session import Screen

logger = get_logger("telegram")


def make_bulk_ops_handler(
    authorization: OwnerAuthorization,
    router: Router,
    workspaces_service: WorkspaceApplicationService,
    group_manager: GroupManagerApplicationService | None = None,
):
    group_manager = group_manager or GroupManagerApplicationService()

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

        session_key = str(chat.id)
        data = query.data or ""

        if data == "bulk:menu":
            await query.answer()
            router.bulk_ops(chat.id)
            await _safe_edit(query, bulk_ops_menu(workspace.name), bulk_ops_keyboard())
        elif data == "bulk:dashboard":
            await query.answer()
            group_manager.leave_session(session_key=session_key)
            router.dashboard(chat.id, workspace.name)
            item = workspaces_service.navigation_item(workspace.name)
            await _safe_edit(query, dashboard(item), dashboard_keyboard())
        elif data == "bulk:group_manager":
            await query.answer()
            session = group_manager.ensure_session(workspace, session_key=session_key)
            router.group_manager(chat.id)
            await _safe_edit(
                query,
                gm_menu(workspace.name, working_set=session.working_set),
                gm_menu_keyboard(has_working_set=session.has_working_set),
            )
        elif data == "gm:check":
            await query.answer()
            await cleanup_temporary(context.bot, router, chat.id)
            group_manager.ensure_session(workspace, session_key=session_key)
            await _show_backup_list(query, router, group_manager, workspace, chat.id)
        elif data == "gm:working_set":
            await query.answer()
            working_set = group_manager.working_set(session_key=session_key)
            if working_set is None:
                await query.answer("Run Check Group IDs first.", show_alert=True)
                return
            router.gm_working_set(chat.id)
            await _safe_edit(
                query,
                gm_working_set(working_set),
                gm_actions_keyboard(group_manager.list_actions()),
            )
        elif data.startswith("gm:action:"):
            await query.answer()
            action_id = data.removeprefix("gm:action:")
            try:
                info = group_manager.action(action_id)
            except GroupManagerError:
                return
            await _safe_edit(
                query,
                gm_coming_soon(info.label, info.description),
                gm_coming_soon_keyboard(),
            )
        elif data.startswith("gm:backup:"):
            await query.answer()
            backup_name = data.removeprefix("gm:backup:")
            router.gm_check_query(chat.id, backup_name)
            await _safe_edit(
                query,
                gm_select_query(backup_name),
                gm_query_keyboard(backup_name),
            )
        elif data.startswith("gm:query:"):
            await query.answer()
            backup_name = data.removeprefix("gm:query:")
            begin_temporary(router, chat.id)
            session = router.gm_check_input(chat.id, backup_name)
            if query.message is not None:
                router.remember_message(chat.id, query.message.message_id)
            await _safe_edit(
                query,
                gm_ask_group_ids(backup_name),
                gm_input_keyboard(),
            )
            session.current_action = backup_name
        elif data == "gm:confirm":
            await query.answer()
            await _run_confirmed(
                update, context, router, group_manager, workspace, chat.id
            )

    return handle


def make_group_manager_text_handler(
    authorization: OwnerAuthorization,
    router: Router,
    workspaces_service: WorkspaceApplicationService,
    group_manager: GroupManagerApplicationService | None = None,
):
    group_manager = group_manager or GroupManagerApplicationService()

    async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not authorization.allows_update(update) or update.effective_message is None:
            return
        chat = update.effective_chat
        if chat is None:
            return
        session = router.session(chat.id)
        if session.current_screen is not Screen.GM_CHECK_INPUT:
            return

        workspace = _resolve_workspace(router, workspaces_service, chat.id)
        if workspace is None:
            return

        backup_name = session.current_action or ""
        raw = (update.effective_message.text or "").strip()
        track_temporary(router, chat.id, update.effective_message.message_id)
        try:
            group_ids = parse_group_ids(raw)
        except ValueError as exc:
            sent = await update.effective_message.reply_text(gm_invalid_ids(str(exc)))
            track_temporary(router, chat.id, sent.message_id)
            return

        sources = group_manager.list_backups(workspace)
        source = next((item for item in sources if item.name == backup_name), None)
        users = source.users if source is not None else 0

        router.gm_check_confirm(chat.id, backup_name, group_ids)
        text = gm_confirmation(workspace.name, backup_name, group_ids, users)
        message_id = session.last_message_id
        if message_id is not None:
            try:
                await context.bot.edit_message_text(
                    chat_id=chat.id,
                    message_id=message_id,
                    text=text,
                    reply_markup=gm_confirm_keyboard(),
                )
                return
            except BadRequest:
                track_temporary(router, chat.id, message_id)
        sent = await update.effective_message.reply_text(
            text, reply_markup=gm_confirm_keyboard()
        )
        router.remember_message(chat.id, sent.message_id)

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


async def _show_backup_list(query, router, service, workspace, chat_id) -> None:
    sources = service.list_backups(workspace)
    if not sources:
        router.group_manager(chat_id)
        await _safe_edit(query, gm_no_backups(), gm_menu_keyboard(has_working_set=False))
        return
    router.gm_check_backup(chat_id)
    await _safe_edit(
        query,
        gm_select_backup(sources),
        gm_backups_keyboard([source.name for source in sources]),
    )


async def _run_confirmed(update, context, router, service, workspace, chat_id) -> None:
    query = update.callback_query
    session = router.session(chat_id)
    action = session.current_action or ""
    if "|" not in action:
        await _safe_edit(query, gm_error("Confirmation expired. Start again."), gm_menu_keyboard(False))
        router.group_manager(chat_id)
        return
    backup_name, encoded = action.split("|", 1)
    try:
        group_ids = parse_group_ids(encoded.replace(",", " "))
    except ValueError as exc:
        await _safe_edit(query, gm_error(str(exc)), gm_menu_keyboard(False))
        router.group_manager(chat_id)
        return

    message_id = query.message.message_id if query.message is not None else session.last_message_id
    router.remember_message(chat_id, message_id)
    await _safe_edit_message(context, chat_id, message_id, gm_progress("Loading backup…"))

    try:
        working_set = await asyncio.to_thread(
            lambda: service.run_check(
                workspace,
                backup_name,
                GroupQueryDescriptor(GroupQueryType.REQUIRED_GROUPS, group_ids),
                session_key=str(chat_id),
            )
        )
    except GroupManagerError as exc:
        router.group_manager(chat_id)
        await cleanup_temporary(context.bot, router, chat_id, keep=message_id)
        await _safe_edit_message(
            context, chat_id, message_id, gm_error(str(exc)), gm_menu_keyboard(False)
        )
        return
    except Exception:  # noqa: BLE001
        logger.exception("Unexpected error during Telegram Group Manager check")
        router.group_manager(chat_id)
        await cleanup_temporary(context.bot, router, chat_id, keep=message_id)
        await _safe_edit_message(
            context, chat_id, message_id, gm_error(), gm_menu_keyboard(False)
        )
        return

    router.gm_working_set(chat_id)
    await cleanup_temporary(context.bot, router, chat_id, keep=message_id)
    await _safe_edit_message(
        context,
        chat_id,
        message_id,
        gm_working_set(working_set),
        gm_actions_keyboard(service.list_actions()),
    )


async def _safe_edit(query, text: str, reply_markup=None) -> None:
    try:
        await query.edit_message_text(text, reply_markup=reply_markup)
    except BadRequest as exc:
        if "not modified" not in str(exc).lower():
            raise


async def _safe_edit_message(context, chat_id, message_id, text, reply_markup=None) -> None:
    if message_id is None:
        return
    try:
        await context.bot.edit_message_text(
            chat_id=chat_id, message_id=message_id, text=text, reply_markup=reply_markup
        )
    except BadRequest as exc:
        if "not modified" not in str(exc).lower():
            raise
