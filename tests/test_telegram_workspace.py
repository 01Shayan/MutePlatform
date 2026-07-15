"""Telegram Workspace Management — Add / Edit / Delete / Status."""

from __future__ import annotations

import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

pytest.importorskip("telegram")

from mute.core.workspace import WorkspaceStore
from mute.interfaces.telegram.auth import OwnerAuthorization
from mute.interfaces.telegram.handlers.workspace import (
    make_workspace_handler,
    make_workspace_text_handler,
)
from mute.interfaces.telegram.messages import dashboard, status_label
from mute.interfaces.telegram.router import Router
from mute.interfaces.telegram.session import Screen, SessionManager
from mute.services.workspace import (
    ConnectionStatus,
    WorkspaceApplicationService,
    WorkspaceNavigationItem,
)

CHAT_ID = 42
OWNER_ID = 1


def _store(tmp_path) -> WorkspaceStore:
    return WorkspaceStore(
        root=tmp_path / "workspaces", registry_path=tmp_path / "config" / "workspaces.json"
    )


def _service(tmp_path) -> WorkspaceApplicationService:
    return WorkspaceApplicationService(_store(tmp_path))


def _make_context():
    bot = SimpleNamespace(edit_message_text=AsyncMock(), delete_message=AsyncMock())
    return SimpleNamespace(bot=bot, application=SimpleNamespace(bot_data={}))


def _make_callback(data: str):
    query = SimpleNamespace(
        data=data,
        answer=AsyncMock(),
        edit_message_text=AsyncMock(),
        message=SimpleNamespace(message_id=555),
    )
    update = SimpleNamespace(
        effective_user=SimpleNamespace(id=OWNER_ID),
        effective_chat=SimpleNamespace(id=CHAT_ID),
        callback_query=query,
        effective_message=None,
    )
    return update, query


def _make_text(text: str):
    message = SimpleNamespace(text=text, reply_text=AsyncMock(), message_id=900)
    update = SimpleNamespace(
        effective_user=SimpleNamespace(id=OWNER_ID),
        effective_chat=SimpleNamespace(id=CHAT_ID),
        effective_message=message,
        callback_query=None,
    )
    return update, message


def _handlers(tmp_path, *, workspace_name: str | None = None):
    service = _service(tmp_path)
    sessions = SessionManager()
    if workspace_name:
        sessions.get(CHAT_ID).current_workspace = workspace_name
    router = Router(sessions)
    auth = OwnerAuthorization(frozenset({OWNER_ID}))
    return (
        make_workspace_handler(auth, router, service),
        make_workspace_text_handler(auth, router, service),
        service,
        sessions,
        router,
    )


def test_status_labels():
    assert "Connected" in status_label(ConnectionStatus.CONNECTED)
    assert "Offline" in status_label(ConnectionStatus.OFFLINE)
    assert "Unknown" in status_label(ConnectionStatus.UNKNOWN)
    text = dashboard(WorkspaceNavigationItem("Prod", "PasarGuard", ConnectionStatus.UNKNOWN))
    assert "⚪ Unknown" in text
    assert "Not checked" not in text


def test_unauthorized_callback_ignored(tmp_path):
    cb, _, _, _, _ = _handlers(tmp_path)
    update, query = _make_callback("ws:add")
    update.effective_user = SimpleNamespace(id=999)
    asyncio.run(cb(update, _make_context()))
    query.answer.assert_not_awaited()


def test_add_workspace_starts_wizard(tmp_path):
    cb, _, _, sessions, _ = _handlers(tmp_path)
    update, query = _make_callback("ws:add")
    asyncio.run(cb(update, _make_context()))
    session = sessions.get(CHAT_ID)
    assert session.current_screen is Screen.WS_ADD_NAME
    assert session.draft["mode"] == "add"
    assert "workspace name" in query.edit_message_text.await_args.args[0].lower()


def test_add_wizard_name_to_integration_to_url(tmp_path):
    cb, text_h, _, sessions, _ = _handlers(tmp_path)
    update, _ = _make_callback("ws:add")
    asyncio.run(cb(update, _make_context()))
    context = _make_context()
    sessions.get(CHAT_ID).last_message_id = 555
    update, _ = _make_text("Alpha")
    assert asyncio.run(text_h(update, context)) is True
    assert sessions.get(CHAT_ID).current_screen is Screen.WS_ADD_INTEGRATION
    assert sessions.get(CHAT_ID).draft["name"] == "Alpha"
    edited = context.bot.edit_message_text.await_args
    text = edited.kwargs.get("text") or edited.args[0]
    assert "Select Integration" in text

    update, query = _make_callback("ws:integration:pasarguard")
    asyncio.run(cb(update, _make_context()))
    assert sessions.get(CHAT_ID).draft["integration"] == "pasarguard"
    assert sessions.get(CHAT_ID).current_screen is Screen.WS_ADD_URL
    assert "Panel URL" in query.edit_message_text.await_args.args[0]


def test_add_wizard_rejects_invalid_url_and_empty_fields(tmp_path):
    _, text_h, _, sessions, router = _handlers(tmp_path)
    sessions.get(CHAT_ID).draft = {"mode": "add", "name": "Alpha", "integration": "pasarguard"}
    router.go_to(CHAT_ID, Screen.WS_ADD_URL)
    update, message = _make_text("not-a-url")
    assert asyncio.run(text_h(update, _make_context())) is True
    message.reply_text.assert_awaited()
    assert "http://" in message.reply_text.await_args.args[0].lower() or "https://" in message.reply_text.await_args.args[0].lower()

    router.go_to(CHAT_ID, Screen.WS_ADD_USERNAME)
    update, message = _make_text("  ")
    asyncio.run(text_h(update, _make_context()))
    assert "Username" in message.reply_text.await_args.args[0]


def test_add_workspace_create_with_probe(tmp_path):
    cb, text_h, service, sessions, router = _handlers(tmp_path)
    sessions.get(CHAT_ID).draft = {
        "mode": "add",
        "name": "Alpha",
        "integration": "pasarguard",
        "integration_label": "PasarGuard",
        "base_url": "https://panel.example",
        "auth": "password",
        "username": "admin",
        "password": "secret",
        "verify_ssl": True,
        "probe_ok": True,
    }
    router.go_to(CHAT_ID, Screen.WS_ADD_CONFIRM)
    update, query = _make_callback("ws:confirm-create")
    asyncio.run(cb(update, _make_context()))
    assert service.workspace("Alpha") is not None
    assert sessions.get(CHAT_ID).current_screen is Screen.DASHBOARD
    assert sessions.get(CHAT_ID).current_workspace == "Alpha"
    assert "created successfully" in query.edit_message_text.await_args.args[0]
    assert service.navigation_item("Alpha").status is ConnectionStatus.CONNECTED


def test_add_token_auth_path(tmp_path):
    cb, text_h, _, sessions, router = _handlers(tmp_path)
    sessions.get(CHAT_ID).draft = {
        "mode": "add",
        "name": "Tok",
        "integration": "pasarguard",
        "base_url": "https://panel",
        "auth": "token",
    }
    router.go_to(CHAT_ID, Screen.WS_ADD_AUTH)
    update, query = _make_callback("ws:auth:token")
    asyncio.run(cb(update, _make_context()))
    assert sessions.get(CHAT_ID).current_screen is Screen.WS_ADD_TOKEN
    assert "Bearer Token" in query.edit_message_text.await_args.args[0]

    update, _ = _make_text("bearer-xyz")
    asyncio.run(text_h(update, _make_context()))
    assert sessions.get(CHAT_ID).draft["token"] == "bearer-xyz"
    assert sessions.get(CHAT_ID).current_screen is Screen.WS_ADD_SSL


def test_ssl_triggers_probe_then_confirm(tmp_path):
    cb, _, _, sessions, router = _handlers(tmp_path)
    sessions.get(CHAT_ID).draft = {
        "mode": "add",
        "name": "Alpha",
        "integration": "pasarguard",
        "integration_label": "PasarGuard",
        "base_url": "https://panel",
        "auth": "password",
        "username": "a",
        "password": "b",
    }
    router.go_to(CHAT_ID, Screen.WS_ADD_SSL)
    client = MagicMock()
    client.test_connection.return_value = True
    update, _ = _make_callback("ws:ssl:yes")
    context = _make_context()
    with patch("mute.services.workspace.service.create_client", return_value=client):
        asyncio.run(cb(update, context))
    assert sessions.get(CHAT_ID).draft["probe_ok"] is True
    assert sessions.get(CHAT_ID).current_screen is Screen.WS_ADD_CONFIRM
    # Last bot edit is the confirmation (after verifying)
    texts = [
        (call.kwargs.get("text") or (call.args[0] if call.args else ""))
        for call in context.bot.edit_message_text.await_args_list
    ]
    assert any("Create Workspace" in text for text in texts)
    assert any("🟢 Connected" in text for text in texts)


def test_edit_and_delete_workspace(tmp_path):
    cb, text_h, service, sessions, router = _handlers(tmp_path)
    service.create(
        name="Prod",
        integration="pasarguard",
        connection={
            "base_url": "https://old",
            "username": "admin",
            "password": "pw",
            "verify_ssl": True,
        },
    )
    sessions.get(CHAT_ID).current_workspace = "Prod"
    router.dashboard(CHAT_ID, "Prod")

    update, query = _make_callback("ws:edit")
    asyncio.run(cb(update, _make_context()))
    assert sessions.get(CHAT_ID).current_screen is Screen.WS_EDIT_NAME
    assert sessions.get(CHAT_ID).draft["original_name"] == "Prod"

    update, _ = _make_text("Prod2")
    asyncio.run(text_h(update, _make_context()))
    assert sessions.get(CHAT_ID).draft["name"] == "Prod2"
    assert sessions.get(CHAT_ID).current_screen is Screen.WS_EDIT_URL

    # Jump to confirm and save
    sessions.get(CHAT_ID).draft.update(
        {
            "base_url": "https://new",
            "auth": "password",
            "username": "admin",
            "password": "pw",
            "verify_ssl": False,
            "probe_ok": False,
        }
    )
    router.go_to(CHAT_ID, Screen.WS_EDIT_CONFIRM)
    update, query = _make_callback("ws:confirm-update")
    asyncio.run(cb(update, _make_context()))
    assert service.workspace("Prod") is None
    assert service.workspace("Prod2") is not None
    assert service.navigation_item("Prod2").status is ConnectionStatus.OFFLINE
    assert "updated successfully" in query.edit_message_text.await_args.args[0]

    # Delete
    sessions.get(CHAT_ID).current_workspace = "Prod2"
    update, query = _make_callback("ws:delete")
    asyncio.run(cb(update, _make_context()))
    assert sessions.get(CHAT_ID).current_screen is Screen.WS_DELETE_CONFIRM
    assert "Are you sure" in query.edit_message_text.await_args.args[0]

    update, query = _make_callback("ws:delete-confirm")
    asyncio.run(cb(update, _make_context()))
    assert service.workspace("Prod2") is None
    assert sessions.get(CHAT_ID).current_screen is Screen.WORKSPACES
    assert "deleted successfully" in query.edit_message_text.await_args.args[0]


def test_delete_cancel_returns_to_dashboard(tmp_path):
    cb, _, service, sessions, router = _handlers(tmp_path)
    service.create(
        name="Prod",
        integration="pasarguard",
        connection={"base_url": "https://panel", "username": "a", "password": "b"},
    )
    sessions.get(CHAT_ID).current_workspace = "Prod"
    router.go_to(CHAT_ID, Screen.WS_DELETE_CONFIRM, action="Prod")
    update, query = _make_callback("ws:delete-cancel")
    asyncio.run(cb(update, _make_context()))
    assert sessions.get(CHAT_ID).current_screen is Screen.DASHBOARD
    assert service.workspace("Prod") is not None


def test_cancel_add_returns_to_workspace_list(tmp_path):
    cb, _, _, sessions, _ = _handlers(tmp_path)
    update, _ = _make_callback("ws:add")
    asyncio.run(cb(update, _make_context()))
    update, query = _make_callback("ws:cancel")
    asyncio.run(cb(update, _make_context()))
    assert sessions.get(CHAT_ID).current_screen is Screen.WORKSPACES
    assert sessions.get(CHAT_ID).draft == {}


def test_edit_keep_password_with_dash(tmp_path):
    _, text_h, _, sessions, router = _handlers(tmp_path)
    sessions.get(CHAT_ID).draft = {
        "mode": "edit",
        "original_name": "Prod",
        "name": "Prod",
        "password": "kept",
        "username": "admin",
        "auth": "password",
        "base_url": "https://panel",
    }
    router.go_to(CHAT_ID, Screen.WS_EDIT_PASSWORD)
    update, _ = _make_text("-")
    asyncio.run(text_h(update, _make_context()))
    assert sessions.get(CHAT_ID).draft["password"] == "kept"
    assert sessions.get(CHAT_ID).current_screen is Screen.WS_EDIT_SSL


def test_text_handler_ignores_other_screens(tmp_path):
    _, text_h, _, sessions, router = _handlers(tmp_path)
    router.go_to(CHAT_ID, Screen.HOME)
    update, message = _make_text("hello")
    assert asyncio.run(text_h(update, _make_context())) is False
    message.reply_text.assert_not_awaited()


def test_edit_missing_workspace_alerts(tmp_path):
    cb, _, _, sessions, router = _handlers(tmp_path)
    sessions.get(CHAT_ID).current_workspace = "Gone"
    router.dashboard(CHAT_ID, "Gone")
    update, query = _make_callback("ws:edit")
    asyncio.run(cb(update, _make_context()))
    query.answer.assert_awaited_with("Workspace is no longer available.", show_alert=True)


def test_delete_missing_workspace_alerts(tmp_path):
    cb, _, _, sessions, _ = _handlers(tmp_path)
    sessions.get(CHAT_ID).current_workspace = None
    update, query = _make_callback("ws:delete")
    asyncio.run(cb(update, _make_context()))
    query.answer.assert_awaited_with("Workspace is no longer available.", show_alert=True)


def test_integration_soon_and_password_auth(tmp_path):
    cb, _, _, sessions, router = _handlers(tmp_path)
    sessions.get(CHAT_ID).draft = {"mode": "add", "name": "Alpha"}
    router.go_to(CHAT_ID, Screen.WS_ADD_INTEGRATION)
    update, query = _make_callback("ws:integration-soon:marzban")
    asyncio.run(cb(update, _make_context()))
    query.answer.assert_awaited()
    assert query.answer.await_args.kwargs.get("show_alert") is True

    sessions.get(CHAT_ID).draft = {
        "mode": "add",
        "name": "Alpha",
        "integration": "pasarguard",
        "base_url": "https://panel",
    }
    router.go_to(CHAT_ID, Screen.WS_ADD_AUTH)
    update, query = _make_callback("ws:auth:password")
    asyncio.run(cb(update, _make_context()))
    assert sessions.get(CHAT_ID).current_screen is Screen.WS_ADD_USERNAME
    assert "Username" in query.edit_message_text.await_args.args[0]


def test_password_and_token_validation_and_keep_token(tmp_path):
    _, text_h, _, sessions, router = _handlers(tmp_path)
    sessions.get(CHAT_ID).draft = {
        "mode": "add",
        "name": "Alpha",
        "auth": "password",
        "base_url": "https://panel",
        "username": "admin",
    }
    router.go_to(CHAT_ID, Screen.WS_ADD_PASSWORD)
    update, message = _make_text("")
    asyncio.run(text_h(update, _make_context()))
    assert "Password" in message.reply_text.await_args.args[0]

    sessions.get(CHAT_ID).draft = {
        "mode": "edit",
        "original_name": "Prod",
        "name": "Prod",
        "auth": "token",
        "token": "old-token",
        "base_url": "https://panel",
    }
    router.go_to(CHAT_ID, Screen.WS_EDIT_TOKEN)
    update, _ = _make_text("-")
    asyncio.run(text_h(update, _make_context()))
    assert sessions.get(CHAT_ID).draft["token"] == "old-token"

    router.go_to(CHAT_ID, Screen.WS_EDIT_TOKEN)
    update, message = _make_text("")
    asyncio.run(text_h(update, _make_context()))
    assert "Token" in message.reply_text.await_args.args[0]


def test_cancel_edit_returns_to_dashboard(tmp_path):
    cb, _, service, sessions, router = _handlers(tmp_path)
    service.create(
        name="Prod",
        integration="pasarguard",
        connection={"base_url": "https://panel", "username": "a", "password": "b"},
    )
    sessions.get(CHAT_ID).current_workspace = "Prod"
    sessions.get(CHAT_ID).draft = {"mode": "edit"}
    router.go_to(CHAT_ID, Screen.WS_EDIT_NAME)
    update, query = _make_callback("ws:cancel-edit")
    asyncio.run(cb(update, _make_context()))
    assert sessions.get(CHAT_ID).current_screen is Screen.DASHBOARD
    assert sessions.get(CHAT_ID).draft == {}


def test_create_failure_shows_error(tmp_path):
    cb, _, service, sessions, router = _handlers(tmp_path)
    sessions.get(CHAT_ID).draft = {
        "mode": "add",
        "name": "Alpha",
        "integration": "pasarguard",
        "base_url": "https://panel",
        "auth": "password",
        "username": "a",
        "password": "b",
        "verify_ssl": True,
        "probe_ok": False,
    }
    router.go_to(CHAT_ID, Screen.WS_ADD_CONFIRM)
    with patch.object(service, "create", side_effect=RuntimeError("boom")):
        update, query = _make_callback("ws:confirm-create")
        asyncio.run(cb(update, _make_context()))
    assert "boom" in query.edit_message_text.await_args.args[0]


def test_update_missing_original_and_rename_failure(tmp_path):
    cb, _, service, sessions, router = _handlers(tmp_path)
    sessions.get(CHAT_ID).draft = {
        "mode": "edit",
        "original_name": "Missing",
        "name": "Missing",
        "integration": "pasarguard",
        "base_url": "https://panel",
        "auth": "password",
        "username": "a",
        "password": "b",
        "verify_ssl": True,
    }
    router.go_to(CHAT_ID, Screen.WS_EDIT_CONFIRM)
    update, query = _make_callback("ws:confirm-update")
    asyncio.run(cb(update, _make_context()))
    assert "no longer available" in query.edit_message_text.await_args.args[0].lower()

    service.create(
        name="Prod",
        integration="pasarguard",
        connection={"base_url": "https://panel", "username": "a", "password": "b"},
    )
    sessions.get(CHAT_ID).draft = {
        "mode": "edit",
        "original_name": "Prod",
        "name": "Renamed",
        "integration": "pasarguard",
        "base_url": "https://panel",
        "auth": "token",
        "token": "tok",
        "verify_ssl": True,
        "probe_ok": True,
    }
    router.go_to(CHAT_ID, Screen.WS_EDIT_CONFIRM)
    with patch.object(service, "update", return_value=None):
        update, query = _make_callback("ws:confirm-update")
        asyncio.run(cb(update, _make_context()))
    assert "Could not rename" in query.edit_message_text.await_args.args[0]


def test_delete_missing_during_confirm(tmp_path):
    cb, _, _, sessions, router = _handlers(tmp_path)
    router.go_to(CHAT_ID, Screen.WS_DELETE_CONFIRM, action="Ghost")
    sessions.get(CHAT_ID).current_workspace = "Ghost"
    update, query = _make_callback("ws:delete-confirm")
    asyncio.run(cb(update, _make_context()))
    assert sessions.get(CHAT_ID).current_screen is Screen.WORKSPACES
    assert "no longer available" in query.edit_message_text.await_args.args[0].lower()


def test_username_step_then_password(tmp_path):
    _, text_h, _, sessions, router = _handlers(tmp_path)
    sessions.get(CHAT_ID).draft = {
        "mode": "add",
        "name": "Alpha",
        "auth": "password",
        "base_url": "https://panel",
    }
    sessions.get(CHAT_ID).last_message_id = 555
    router.go_to(CHAT_ID, Screen.WS_ADD_USERNAME)
    update, _ = _make_text("admin")
    context = _make_context()
    asyncio.run(text_h(update, context))
    assert sessions.get(CHAT_ID).draft["username"] == "admin"
    assert sessions.get(CHAT_ID).current_screen is Screen.WS_ADD_PASSWORD


def test_url_and_password_success_paths(tmp_path):
    _, text_h, _, sessions, router = _handlers(tmp_path)
    sessions.get(CHAT_ID).draft = {"mode": "add", "name": "Alpha", "integration": "pasarguard"}
    sessions.get(CHAT_ID).last_message_id = 555
    router.go_to(CHAT_ID, Screen.WS_ADD_URL)
    update, _ = _make_text("https://panel.example/")
    context = _make_context()
    asyncio.run(text_h(update, context))
    assert sessions.get(CHAT_ID).draft["base_url"] == "https://panel.example"
    assert sessions.get(CHAT_ID).current_screen is Screen.WS_ADD_AUTH

    sessions.get(CHAT_ID).draft.update({"auth": "password", "username": "admin"})
    router.go_to(CHAT_ID, Screen.WS_ADD_PASSWORD)
    update, _ = _make_text("secret")
    asyncio.run(text_h(update, _make_context()))
    assert sessions.get(CHAT_ID).draft["password"] == "secret"
    assert sessions.get(CHAT_ID).current_screen is Screen.WS_ADD_SSL


def test_unavailable_integration_alerts(tmp_path):
    cb, _, _, sessions, router = _handlers(tmp_path)
    sessions.get(CHAT_ID).draft = {"mode": "add", "name": "Alpha"}
    router.go_to(CHAT_ID, Screen.WS_ADD_INTEGRATION)
    update, query = _make_callback("ws:integration:does-not-exist")
    asyncio.run(cb(update, _make_context()))
    query.answer.assert_awaited_with("Coming in the next phase.", show_alert=True)


def test_cancel_edit_falls_back_to_workspace_list(tmp_path):
    cb, _, _, sessions, router = _handlers(tmp_path)
    sessions.get(CHAT_ID).current_workspace = "Gone"
    sessions.get(CHAT_ID).draft = {"mode": "edit"}
    router.go_to(CHAT_ID, Screen.WS_EDIT_NAME)
    update, query = _make_callback("ws:cancel-edit")
    asyncio.run(cb(update, _make_context()))
    assert sessions.get(CHAT_ID).current_screen is Screen.WORKSPACES


def test_edit_or_reply_falls_back_on_bad_request(tmp_path):
    from telegram.error import BadRequest

    _, text_h, _, sessions, router = _handlers(tmp_path)
    sessions.get(CHAT_ID).draft = {"mode": "add"}
    sessions.get(CHAT_ID).last_message_id = 555
    router.go_to(CHAT_ID, Screen.WS_ADD_NAME)
    context = _make_context()
    context.bot.edit_message_text = AsyncMock(side_effect=BadRequest("message is not modified"))
    update, message = _make_text("Fresh")
    asyncio.run(text_h(update, context))
    message.reply_text.assert_awaited()
    assert sessions.get(CHAT_ID).draft["name"] == "Fresh"


def test_safe_edit_ignores_not_modified(tmp_path):
    from telegram.error import BadRequest

    cb, _, _, _, _ = _handlers(tmp_path)
    update, query = _make_callback("ws:add")
    query.edit_message_text = AsyncMock(side_effect=BadRequest("Message is not modified"))
    asyncio.run(cb(update, _make_context()))
