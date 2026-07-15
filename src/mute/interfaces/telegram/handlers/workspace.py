"""Telegram workspace management — Add / Edit / Delete via WorkspaceApplicationService."""

from __future__ import annotations

import asyncio

from telegram import Update
from telegram.error import BadRequest
from telegram.ext import ContextTypes

from ....core.logging import get_logger, use_workspace
from ....services.workspace import (
    ConnectionStatus,
    WorkspaceApplicationService,
    WorkspaceOperationError,
)
from ..auth import OwnerAuthorization
from ..keyboards import (
    auth_method_keyboard,
    cancel_keyboard,
    dashboard_keyboard,
    integrations_keyboard,
    verify_ssl_keyboard,
    workspaces_keyboard,
    yes_no_keyboard,
)
from ..messages import (
    ask_panel_url,
    ask_password,
    ask_token,
    ask_username,
    ask_workspace_name,
    coming_next_phase,
    dashboard,
    delete_workspace_confirmation,
    select_auth_method,
    select_integration,
    select_verify_ssl,
    verifying_connection,
    workspace_confirmation,
    workspace_created,
    workspace_deleted,
    workspace_error,
    workspace_updated,
    workspaces,
)
from ..router import Router
from ..session import Screen

logger = get_logger("telegram")

_TEXT_SCREENS = {
    Screen.WS_ADD_NAME,
    Screen.WS_ADD_URL,
    Screen.WS_ADD_USERNAME,
    Screen.WS_ADD_PASSWORD,
    Screen.WS_ADD_TOKEN,
    Screen.WS_EDIT_NAME,
    Screen.WS_EDIT_URL,
    Screen.WS_EDIT_USERNAME,
    Screen.WS_EDIT_PASSWORD,
    Screen.WS_EDIT_TOKEN,
}


def make_workspace_handler(
    authorization: OwnerAuthorization,
    router: Router,
    workspaces_service: WorkspaceApplicationService,
):
    async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not authorization.allows_update(update) or update.callback_query is None:
            return
        query = update.callback_query
        chat = update.effective_chat
        if chat is None:
            return
        data = query.data or ""
        session = router.session(chat.id)

        if data == "ws:add":
            await query.answer()
            session.draft = {"mode": "add"}
            router.go_to(chat.id, Screen.WS_ADD_NAME)
            if query.message is not None:
                router.remember_message(chat.id, query.message.message_id)
            await _safe_edit(query, ask_workspace_name(), cancel_keyboard("ws:cancel"))
        elif data == "ws:edit":
            workspace = _resolve_workspace(router, workspaces_service, chat.id)
            if workspace is None:
                await query.answer("Workspace is no longer available.", show_alert=True)
                return
            await query.answer()
            nav = workspaces_service.navigation_item(workspace.name)
            session.draft = {
                "mode": "edit",
                "original_name": workspace.name,
                "name": workspace.name,
                "integration": workspace.integration,
                "integration_label": nav.panel if nav is not None else workspace.integration,
                "base_url": workspace.base_url,
                "auth": "token" if workspace.token and not workspace.has_credentials else "password",
                "username": workspace.username,
                "password": workspace.password,
                "token": workspace.token,
                "verify_ssl": workspace.verify_ssl,
            }
            router.go_to(chat.id, Screen.WS_EDIT_NAME)
            if query.message is not None:
                router.remember_message(chat.id, query.message.message_id)
            await _safe_edit(
                query,
                ask_workspace_name(current=workspace.name),
                cancel_keyboard("ws:cancel-edit"),
            )
        elif data == "ws:delete":
            name = session.current_workspace
            if not name:
                await query.answer("Workspace is no longer available.", show_alert=True)
                return
            await query.answer()
            router.go_to(chat.id, Screen.WS_DELETE_CONFIRM, action=name)
            await _safe_edit(
                query,
                delete_workspace_confirmation(name),
                yes_no_keyboard("ws:delete-confirm", "ws:delete-cancel"),
            )
        elif data == "ws:delete-confirm":
            await query.answer()
            await _delete_workspace(query, router, workspaces_service, chat.id)
        elif data == "ws:delete-cancel":
            await query.answer()
            await _show_dashboard(query, router, workspaces_service, chat.id)
        elif data == "ws:cancel":
            await query.answer()
            router.clear_draft(chat.id)
            router.workspaces(chat.id)
            items = workspaces_service.navigation_items()
            await _safe_edit(
                query, workspaces(items), workspaces_keyboard([item.name for item in items])
            )
        elif data == "ws:cancel-edit":
            await query.answer()
            router.clear_draft(chat.id)
            await _show_dashboard(query, router, workspaces_service, chat.id)
        elif data.startswith("ws:integration-soon:"):
            await query.answer(coming_next_phase(), show_alert=True)
        elif data.startswith("ws:integration:"):
            key = data.removeprefix("ws:integration:")
            integration = next((item for item in workspaces_service.integrations() if item.key == key), None)
            if integration is None or not workspaces_service.integration_is_available(integration):
                await query.answer(coming_next_phase(), show_alert=True)
                return
            await query.answer()
            session.draft["integration"] = integration.key
            session.draft["integration_label"] = integration.name
            mode = session.draft.get("mode", "add")
            screen = Screen.WS_ADD_URL if mode == "add" else Screen.WS_EDIT_URL
            router.go_to(chat.id, screen)
            await _safe_edit(
                query,
                ask_panel_url(current=session.draft.get("base_url")),
                cancel_keyboard("ws:cancel" if mode == "add" else "ws:cancel-edit"),
            )
        elif data.startswith("ws:auth:"):
            await query.answer()
            method = data.removeprefix("ws:auth:")
            session.draft["auth"] = method
            mode = session.draft.get("mode", "add")
            cancel = "ws:cancel" if mode == "add" else "ws:cancel-edit"
            if method == "password":
                screen = Screen.WS_ADD_USERNAME if mode == "add" else Screen.WS_EDIT_USERNAME
                router.go_to(chat.id, screen)
                await _safe_edit(
                    query,
                    ask_username(current=session.draft.get("username")),
                    cancel_keyboard(cancel),
                )
            else:
                screen = Screen.WS_ADD_TOKEN if mode == "add" else Screen.WS_EDIT_TOKEN
                router.go_to(chat.id, screen)
                await _safe_edit(
                    query,
                    ask_token(keep_allowed=(mode == "edit" and bool(session.draft.get("token")))),
                    cancel_keyboard(cancel),
                )
        elif data.startswith("ws:ssl:"):
            await query.answer()
            session.draft["verify_ssl"] = data.removeprefix("ws:ssl:") == "yes"
            await _probe_and_confirm(query, context, router, workspaces_service, chat.id)
        elif data == "ws:confirm-create":
            await query.answer()
            await _create_workspace(query, router, workspaces_service, chat.id)
        elif data == "ws:confirm-update":
            await query.answer()
            await _update_workspace(query, router, workspaces_service, chat.id)

    return handle


def make_workspace_text_handler(
    authorization: OwnerAuthorization,
    router: Router,
    workspaces_service: WorkspaceApplicationService,
):
    async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
        """Handle wizard text input. Returns True when the update was consumed."""
        if not authorization.allows_update(update) or update.effective_message is None:
            return False
        chat = update.effective_chat
        if chat is None:
            return False
        session = router.session(chat.id)
        if session.current_screen not in _TEXT_SCREENS:
            return False

        text = (update.effective_message.text or "").strip()
        mode = session.draft.get("mode", "add")
        cancel = "ws:cancel" if mode == "add" else "ws:cancel-edit"

        try:
            if session.current_screen in {Screen.WS_ADD_NAME, Screen.WS_EDIT_NAME}:
                current = session.draft.get("original_name") if mode == "edit" else None
                session.draft["name"] = workspaces_service.validate_name(text, current=current)
                if mode == "add":
                    router.go_to(chat.id, Screen.WS_ADD_INTEGRATION)
                    items = [
                        (item.key, item.name, workspaces_service.integration_is_available(item))
                        for item in workspaces_service.integrations()
                    ]
                    await _edit_or_reply(
                        context, router, chat.id, update,
                        select_integration(), integrations_keyboard(items),
                    )
                else:
                    router.go_to(chat.id, Screen.WS_EDIT_URL)
                    await _edit_or_reply(
                        context, router, chat.id, update,
                        ask_panel_url(current=session.draft.get("base_url")),
                        cancel_keyboard(cancel),
                    )
            elif session.current_screen in {Screen.WS_ADD_URL, Screen.WS_EDIT_URL}:
                url = text.rstrip("/")
                if not (url.startswith("http://") or url.startswith("https://")):
                    raise WorkspaceOperationError("URL must start with http:// or https://.")
                session.draft["base_url"] = url
                router.go_to(chat.id, Screen.WS_ADD_AUTH if mode == "add" else Screen.WS_EDIT_AUTH)
                await _edit_or_reply(
                    context, router, chat.id, update,
                    select_auth_method(), auth_method_keyboard(cancel_data=cancel),
                )
            elif session.current_screen in {Screen.WS_ADD_USERNAME, Screen.WS_EDIT_USERNAME}:
                if not text:
                    raise WorkspaceOperationError("Username cannot be empty.")
                session.draft["username"] = text
                session.draft["token"] = None
                screen = Screen.WS_ADD_PASSWORD if mode == "add" else Screen.WS_EDIT_PASSWORD
                router.go_to(chat.id, screen)
                await _edit_or_reply(
                    context, router, chat.id, update,
                    ask_password(keep_allowed=(mode == "edit" and bool(session.draft.get("password")))),
                    cancel_keyboard(cancel),
                )
            elif session.current_screen in {Screen.WS_ADD_PASSWORD, Screen.WS_EDIT_PASSWORD}:
                if mode == "edit" and text == "-":
                    pass  # keep existing password
                elif not text:
                    raise WorkspaceOperationError("Password cannot be empty.")
                else:
                    session.draft["password"] = text
                session.draft["token"] = None
                router.go_to(chat.id, Screen.WS_ADD_SSL if mode == "add" else Screen.WS_EDIT_SSL)
                await _edit_or_reply(
                    context, router, chat.id, update,
                    select_verify_ssl(current=session.draft.get("verify_ssl")),
                    verify_ssl_keyboard(cancel_data=cancel),
                )
            elif session.current_screen in {Screen.WS_ADD_TOKEN, Screen.WS_EDIT_TOKEN}:
                if mode == "edit" and text == "-":
                    pass
                elif not text:
                    raise WorkspaceOperationError("Token cannot be empty.")
                else:
                    session.draft["token"] = text
                session.draft["username"] = None
                session.draft["password"] = None
                router.go_to(chat.id, Screen.WS_ADD_SSL if mode == "add" else Screen.WS_EDIT_SSL)
                await _edit_or_reply(
                    context, router, chat.id, update,
                    select_verify_ssl(current=session.draft.get("verify_ssl")),
                    verify_ssl_keyboard(cancel_data=cancel),
                )
        except WorkspaceOperationError as exc:
            await update.effective_message.reply_text(workspace_error(str(exc)))
        return True

    return handle


def _resolve_workspace(router: Router, service: WorkspaceApplicationService, chat_id: int):
    name = router.session(chat_id).current_workspace
    if not name:
        return None
    workspace = service.workspace(name)
    if workspace is not None:
        use_workspace(workspace.logs_dir)
    return workspace


def _connection_from_draft(draft: dict) -> dict:
    auth = draft.get("auth", "password")
    if auth == "password":
        return {
            "base_url": draft["base_url"],
            "username": draft.get("username"),
            "password": draft.get("password"),
            "token": None,
            "verify_ssl": bool(draft.get("verify_ssl", True)),
        }
    return {
        "base_url": draft["base_url"],
        "username": None,
        "password": None,
        "token": draft.get("token"),
        "verify_ssl": bool(draft.get("verify_ssl", True)),
    }


async def _probe_and_confirm(query, context, router, service, chat_id) -> None:
    session = router.session(chat_id)
    draft = session.draft
    mode = draft.get("mode", "add")
    from ....core.workspace import Workspace

    probe = Workspace(
        name=draft.get("name") or "probe",
        integration=draft.get("integration", "pasarguard"),
        **_connection_from_draft(draft),
    )
    message_id = query.message.message_id if query.message is not None else session.last_message_id
    await _safe_edit_message(context, chat_id, message_id, verifying_connection())
    ok = await asyncio.to_thread(WorkspaceApplicationService.probe_connection, probe)
    draft["probe_ok"] = ok
    title = "Create Workspace" if mode == "add" else "Save Workspace"
    yes = "ws:confirm-create" if mode == "add" else "ws:confirm-update"
    no = "ws:cancel" if mode == "add" else "ws:cancel-edit"
    screen = Screen.WS_ADD_CONFIRM if mode == "add" else Screen.WS_EDIT_CONFIRM
    router.go_to(chat_id, screen)
    await _safe_edit_message(
        context,
        chat_id,
        message_id,
        workspace_confirmation(draft, title=title),
        yes_no_keyboard(yes, no),
    )


async def _create_workspace(query, router, service, chat_id) -> None:
    session = router.session(chat_id)
    draft = session.draft
    try:
        workspace = service.create(
            name=draft["name"],
            integration=draft.get("integration", "pasarguard"),
            connection=_connection_from_draft(draft),
        )
        if "probe_ok" in draft:
            status = ConnectionStatus.CONNECTED if draft["probe_ok"] else ConnectionStatus.OFFLINE
            WorkspaceApplicationService.record_connection_status(workspace, status)
    except Exception as exc:  # noqa: BLE001
        logger.exception("Failed to create workspace via Telegram")
        await _safe_edit(query, workspace_error(str(exc)), cancel_keyboard("ws:cancel"))
        return
    router.clear_draft(chat_id)
    router.dashboard(chat_id, workspace.name)
    item = service.navigation_item(workspace.name)
    await _safe_edit(
        query,
        f"{workspace_created(workspace.name)}\n\n{dashboard(item)}",
        dashboard_keyboard(),
    )


async def _update_workspace(query, router, service, chat_id) -> None:
    session = router.session(chat_id)
    draft = session.draft
    original = service.workspace(draft.get("original_name", ""))
    if original is None:
        await _safe_edit(query, workspace_error("Workspace is no longer available."), cancel_keyboard("ws:cancel-edit"))
        return
    try:
        updated = service.update(
            original,
            name=draft["name"],
            integration=draft.get("integration", original.integration),
            connection=_connection_from_draft(draft),
        )
        if updated is None:
            raise WorkspaceOperationError(f"Could not rename to '{draft['name']}'.")
        if "probe_ok" in draft:
            status = ConnectionStatus.CONNECTED if draft["probe_ok"] else ConnectionStatus.OFFLINE
            WorkspaceApplicationService.record_connection_status(updated, status)
    except (WorkspaceOperationError, Exception) as exc:  # noqa: BLE001
        logger.exception("Failed to update workspace via Telegram")
        await _safe_edit(query, workspace_error(str(exc)), cancel_keyboard("ws:cancel-edit"))
        return
    router.clear_draft(chat_id)
    router.dashboard(chat_id, updated.name)
    item = service.navigation_item(updated.name)
    await _safe_edit(
        query,
        f"{workspace_updated(updated.name)}\n\n{dashboard(item)}",
        dashboard_keyboard(),
    )


async def _delete_workspace(query, router, service, chat_id) -> None:
    session = router.session(chat_id)
    name = session.current_action or session.current_workspace
    workspace = service.workspace(name) if name else None
    if workspace is None:
        await _safe_edit(query, workspace_error("Workspace is no longer available."), workspaces_keyboard([]))
        router.workspaces(chat_id)
        return
    service.delete(workspace)
    session.current_workspace = None
    router.clear_draft(chat_id)
    router.workspaces(chat_id)
    items = service.navigation_items()
    await _safe_edit(
        query,
        f"{workspace_deleted(name)}\n\n{workspaces(items)}",
        workspaces_keyboard([item.name for item in items]),
    )


async def _show_dashboard(query, router, service, chat_id) -> None:
    name = router.session(chat_id).current_workspace
    item = service.navigation_item(name) if name else None
    if item is None:
        router.workspaces(chat_id)
        items = service.navigation_items()
        await _safe_edit(query, workspaces(items), workspaces_keyboard([i.name for i in items]))
        return
    router.dashboard(chat_id, item.name)
    await _safe_edit(query, dashboard(item), dashboard_keyboard())


async def _edit_or_reply(context, router, chat_id, update, text, reply_markup) -> None:
    message_id = router.session(chat_id).last_message_id
    if message_id is not None:
        try:
            await context.bot.edit_message_text(
                chat_id=chat_id, message_id=message_id, text=text, reply_markup=reply_markup
            )
            return
        except BadRequest:
            pass
    sent = await update.effective_message.reply_text(text, reply_markup=reply_markup)
    router.remember_message(chat_id, sent.message_id)


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
