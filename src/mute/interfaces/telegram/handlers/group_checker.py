"""Group Engine Telegram interface — pure interface over GroupCheckerApplicationService."""

from __future__ import annotations

import asyncio

from telegram import Update
from telegram.error import BadRequest
from telegram.ext import ContextTypes

from ....core.logging import get_logger, use_workspace
from ....core.workspace import Workspace
from ....services.group_checker import (
    GroupCheckerApplicationService,
    GroupCheckerOperationError,
    GroupQueryDescriptor,
    GroupQueryType,
    parse_group_ids,
)
from ....services.workspace import WorkspaceApplicationService
from ..auth import OwnerAuthorization
from ..conversation import begin_temporary, cleanup_temporary, track_temporary
from ..keyboards import (
    dashboard_keyboard,
    group_checker_backups_keyboard,
    group_checker_coming_soon_keyboard,
    group_checker_confirm_keyboard,
    group_checker_input_keyboard,
    group_checker_menu_keyboard,
    group_checker_query_keyboard,
    group_checker_result_keyboard,
)
from ..messages import (
    dashboard,
    group_checker_ask_group_ids,
    group_checker_coming_soon,
    group_checker_confirmation,
    group_checker_error,
    group_checker_invalid_ids,
    group_checker_menu,
    group_checker_no_backups,
    group_checker_progress,
    group_checker_result,
    group_checker_select_backup,
    group_checker_select_query,
)
from ..router import Router
from ..session import Screen

logger = get_logger("telegram")

_SOON_OPERATIONS = frozenset({"add", "remove", "replace", "history"})


def make_group_checker_handler(
    authorization: OwnerAuthorization,
    router: Router,
    workspaces_service: WorkspaceApplicationService,
):
    """Build the callback handler for every ``group_checker:*`` action."""

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

        service = GroupCheckerApplicationService()
        data = query.data or ""

        if data == "group_checker:menu":
            await query.answer()
            router.group_checker(chat.id)
            await _safe_edit(query, group_checker_menu(workspace.name), group_checker_menu_keyboard())
        elif data == "group_checker:dashboard":
            await query.answer()
            router.dashboard(chat.id, workspace.name)
            item = workspaces_service.navigation_item(workspace.name)
            await _safe_edit(query, dashboard(item), dashboard_keyboard())
        elif data.startswith("group_checker:soon:"):
            await query.answer()
            operation = data.removeprefix("group_checker:soon:")
            if operation not in _SOON_OPERATIONS:
                return
            await _safe_edit(
                query,
                group_checker_coming_soon(operation),
                group_checker_coming_soon_keyboard(),
            )
        elif data == "group_checker:run":
            await query.answer()
            await cleanup_temporary(context.bot, router, chat.id)
            await _show_backup_list(query, router, service, workspace, chat.id)
        elif data.startswith("group_checker:backup:"):
            await query.answer()
            backup_name = data.removeprefix("group_checker:backup:")
            router.group_checker_query(chat.id, backup_name)
            await _safe_edit(
                query,
                group_checker_select_query(backup_name),
                group_checker_query_keyboard(backup_name),
            )
        elif data.startswith("group_checker:query:"):
            await query.answer()
            backup_name = data.removeprefix("group_checker:query:")
            begin_temporary(router, chat.id)
            session = router.group_checker_input(chat.id, backup_name)
            if query.message is not None:
                router.remember_message(chat.id, query.message.message_id)
            await _safe_edit(
                query,
                group_checker_ask_group_ids(backup_name),
                group_checker_input_keyboard(),
            )
            # Keep session action as backup name for the text handler.
            session.current_action = backup_name
        elif data == "group_checker:confirm":
            await query.answer()
            await _run_confirmed(update, context, router, service, workspace, chat.id)

    return handle


def make_group_checker_text_handler(
    authorization: OwnerAuthorization,
    router: Router,
    workspaces_service: WorkspaceApplicationService,
):
    """Accept free-form group ID messages while the chat waits on the input screen."""

    async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not authorization.allows_update(update) or update.effective_message is None:
            return
        chat = update.effective_chat
        if chat is None:
            return
        session = router.session(chat.id)
        if session.current_screen is not Screen.GROUP_CHECKER_INPUT:
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
            sent = await update.effective_message.reply_text(group_checker_invalid_ids(str(exc)))
            track_temporary(router, chat.id, sent.message_id)
            return

        sources = GroupCheckerApplicationService().list_backups(workspace)
        source = next((item for item in sources if item.name == backup_name), None)
        users = source.users if source is not None else 0

        router.group_checker_confirm(chat.id, backup_name, group_ids)
        text = group_checker_confirmation(workspace.name, backup_name, group_ids, users)
        message_id = session.last_message_id
        if message_id is not None:
            try:
                await context.bot.edit_message_text(
                    chat_id=chat.id,
                    message_id=message_id,
                    text=text,
                    reply_markup=group_checker_confirm_keyboard(),
                )
                return
            except BadRequest:
                track_temporary(router, chat.id, message_id)
        sent = await update.effective_message.reply_text(
            text, reply_markup=group_checker_confirm_keyboard()
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


async def _show_backup_list(query, router: Router, service, workspace, chat_id) -> None:
    sources = service.list_backups(workspace)
    if not sources:
        router.group_checker(chat_id)
        await _safe_edit(query, group_checker_no_backups(), group_checker_menu_keyboard())
        return
    router.group_checker_backup(chat_id)
    await _safe_edit(
        query,
        group_checker_select_backup(sources),
        group_checker_backups_keyboard([source.name for source in sources]),
    )


async def _run_confirmed(update, context, router: Router, service, workspace, chat_id) -> None:
    query = update.callback_query
    session = router.session(chat_id)
    action = session.current_action or ""
    if "|" not in action:
        await _safe_edit(query, group_checker_error("Confirmation expired. Start again."), group_checker_menu_keyboard())
        router.group_checker(chat_id)
        return
    backup_name, encoded = action.split("|", 1)
    try:
        group_ids = parse_group_ids(encoded.replace(",", " "))
    except ValueError as exc:
        await _safe_edit(query, group_checker_error(str(exc)), group_checker_menu_keyboard())
        router.group_checker(chat_id)
        return

    message_id = query.message.message_id if query.message is not None else session.last_message_id
    router.remember_message(chat_id, message_id)
    await _safe_edit_message(context, chat_id, message_id, group_checker_progress("Loading backup…"))

    try:
        result = await asyncio.to_thread(
            service.run_query,
            workspace,
            backup_name,
            GroupQueryDescriptor(GroupQueryType.REQUIRED_GROUPS, group_ids),
        )
    except GroupCheckerOperationError as exc:
        router.group_checker(chat_id)
        await cleanup_temporary(context.bot, router, chat_id, keep=message_id)
        await _safe_edit_message(
            context, chat_id, message_id, group_checker_error(str(exc)), group_checker_menu_keyboard()
        )
        return
    except Exception:  # noqa: BLE001 — surface a friendly message, log the detail
        logger.exception("Unexpected error during Telegram group engine check")
        router.group_checker(chat_id)
        await cleanup_temporary(context.bot, router, chat_id, keep=message_id)
        await _safe_edit_message(
            context, chat_id, message_id, group_checker_error(), group_checker_menu_keyboard()
        )
        return

    router.group_checker_result(chat_id)
    await cleanup_temporary(context.bot, router, chat_id, keep=message_id)
    await _safe_edit_message(
        context, chat_id, message_id, group_checker_result(result), group_checker_result_keyboard()
    )


async def _safe_edit(query, text: str, reply_markup=None) -> None:
    try:
        await query.edit_message_text(text, reply_markup=reply_markup)
    except BadRequest as exc:
        if "not modified" not in str(exc).lower():
            raise


async def _safe_edit_message(context, chat_id: int, message_id: int | None, text: str, reply_markup=None) -> None:
    if message_id is None:
        return
    try:
        await context.bot.edit_message_text(
            chat_id=chat_id, message_id=message_id, text=text, reply_markup=reply_markup
        )
    except BadRequest as exc:
        if "not modified" not in str(exc).lower():
            raise
