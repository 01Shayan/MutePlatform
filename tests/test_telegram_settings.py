"""Telegram Settings interface tests."""

from __future__ import annotations

import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

pytest.importorskip("telegram")

from mute.core import config
from mute.core.workspace import WorkspaceStore
from mute.interfaces.telegram.auth import OwnerAuthorization
from mute.interfaces.telegram.handlers.settings import (
    make_settings_handler,
    make_settings_text_handler,
)
from mute.interfaces.telegram.router import Router
from mute.interfaces.telegram.session import Screen, SessionManager
from mute.services.settings import SettingsApplicationService
from mute.services.workspace import WorkspaceApplicationService

CHAT_ID = 42
OWNER_ID = 1


@pytest.fixture(autouse=True)
def _isolate_config(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "CONFIG_DIR", tmp_path / "config")
    monkeypatch.setattr(config, "SETTINGS_PATH", tmp_path / "config" / "settings.json")
    monkeypatch.setattr(config, "ENV_PATH", tmp_path / ".env")
    config.ensure_settings()


def _workspace_service(tmp_path) -> WorkspaceApplicationService:
    store = WorkspaceStore(
        root=tmp_path / "workspaces", registry_path=tmp_path / "config" / "workspaces.json"
    )
    return WorkspaceApplicationService(store)


def _make_context():
    bot = SimpleNamespace(edit_message_text=AsyncMock())
    return SimpleNamespace(bot=bot)


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


def _handlers(tmp_path):
    sessions = SessionManager()
    router = Router(sessions)
    auth = OwnerAuthorization(frozenset({OWNER_ID}))
    ws = _workspace_service(tmp_path)
    settings = SettingsApplicationService()
    return (
        make_settings_handler(auth, router, ws),
        make_settings_text_handler(auth, router, settings),
        ws,
        sessions,
        router,
    )


def test_unauthorized_ignored(tmp_path):
    cb, _, _, _, _ = _handlers(tmp_path)
    update, query = _make_callback("settings:reset-tokens")
    update.effective_user = SimpleNamespace(id=999)
    asyncio.run(cb(update, _make_context()))
    query.answer.assert_not_awaited()


def test_reset_tokens_confirmation_and_success(tmp_path):
    cb, _, ws, sessions, _ = _handlers(tmp_path)
    ws.create(
        name="A",
        integration="pasarguard",
        connection={"base_url": "https://a", "token": "tok", "username": None, "password": None},
    )
    ws.create(
        name="B",
        integration="pasarguard",
        connection={
            "base_url": "https://b",
            "username": "admin",
            "password": "pw",
            "token": "tok2",
        },
    )

    update, query = _make_callback("settings:reset-tokens")
    asyncio.run(cb(update, _make_context()))
    assert sessions.get(CHAT_ID).current_screen is Screen.SETTINGS_RESET_TOKENS_CONFIRM
    text = query.edit_message_text.await_args.args[0]
    assert "Reset Workspace Tokens" in text
    assert "passwords" in text
    assert "backups" in text

    update, query = _make_callback("settings:reset-tokens-yes")
    asyncio.run(cb(update, _make_context()))
    assert sessions.get(CHAT_ID).current_screen is Screen.SETTINGS
    assert "Workspace tokens removed successfully." in query.edit_message_text.await_args.args[0]
    assert ws.workspace("A").token is None
    assert ws.workspace("B").token is None
    assert ws.workspace("B").password == "pw"
    assert ws.workspace("B").username == "admin"
    assert ws.workspace("A").base_url == "https://a"


def test_reset_tokens_no_cancels(tmp_path):
    cb, _, _, sessions, _ = _handlers(tmp_path)
    update, _ = _make_callback("settings:reset-tokens")
    asyncio.run(cb(update, _make_context()))
    update, query = _make_callback("settings:reset-tokens-no")
    asyncio.run(cb(update, _make_context()))
    assert sessions.get(CHAT_ID).current_screen is Screen.SETTINGS
    assert "Settings" in query.edit_message_text.await_args.args[0]


def test_change_bot_token_flow(tmp_path):
    cb, text_h, _, sessions, router = _handlers(tmp_path)
    update, query = _make_callback("settings:bot-token")
    asyncio.run(cb(update, _make_context()))
    assert sessions.get(CHAT_ID).current_screen is Screen.SETTINGS_BOT_TOKEN_CONFIRM
    assert "Change Bot Token" in query.edit_message_text.await_args.args[0]

    update, query = _make_callback("settings:bot-token-yes")
    asyncio.run(cb(update, _make_context()))
    assert sessions.get(CHAT_ID).current_screen is Screen.SETTINGS_BOT_TOKEN_INPUT

    update, message = _make_text("")
    assert asyncio.run(text_h(update, _make_context())) is True
    message.reply_text.assert_awaited()
    assert "empty" in message.reply_text.await_args.args[0].lower()

    update, message = _make_text("badtoken")
    asyncio.run(text_h(update, _make_context()))
    assert "invalid" in message.reply_text.await_args.args[0].lower()

    update, _ = _make_text("999999:NEW-TOKEN")
    context = _make_context()
    router.remember_message(CHAT_ID, 555)
    asyncio.run(text_h(update, context))
    assert sessions.get(CHAT_ID).current_screen is Screen.SETTINGS
    assert "BOT_TOKEN=999999:NEW-TOKEN" in config.ENV_PATH.read_text(encoding="utf-8")
    text = context.bot.edit_message_text.await_args.kwargs.get("text") or context.bot.edit_message_text.await_args.args[0]
    assert "Bot token updated successfully." in text
    assert "Restart the bot" in text


def test_change_owner_ids_flow(tmp_path):
    cb, text_h, _, sessions, router = _handlers(tmp_path)
    update, query = _make_callback("settings:owner-ids")
    asyncio.run(cb(update, _make_context()))
    assert sessions.get(CHAT_ID).current_screen is Screen.SETTINGS_OWNER_CONFIRM

    update, query = _make_callback("settings:owner-ids-yes")
    asyncio.run(cb(update, _make_context()))
    assert sessions.get(CHAT_ID).current_screen is Screen.SETTINGS_OWNER_INPUT

    update, message = _make_text("not-a-number")
    asyncio.run(text_h(update, _make_context()))
    message.reply_text.assert_awaited()

    update, _ = _make_text("123456789,987654321")
    context = _make_context()
    router.remember_message(CHAT_ID, 555)
    asyncio.run(text_h(update, context))
    assert sessions.get(CHAT_ID).current_screen is Screen.SETTINGS
    text = context.bot.edit_message_text.await_args.kwargs.get("text") or context.bot.edit_message_text.await_args.args[0]
    assert "Owner IDs updated successfully." in text
    assert "Restart the bot" in text
    data = config.SETTINGS_PATH.read_text(encoding="utf-8")
    assert "123456789" in data and "987654321" in data


def test_cancel_returns_to_settings(tmp_path):
    cb, _, _, sessions, _ = _handlers(tmp_path)
    update, _ = _make_callback("settings:bot-token-yes")
    asyncio.run(cb(update, _make_context()))
    assert sessions.get(CHAT_ID).current_screen is Screen.SETTINGS_BOT_TOKEN_INPUT
    update, query = _make_callback("settings:cancel")
    asyncio.run(cb(update, _make_context()))
    assert sessions.get(CHAT_ID).current_screen is Screen.SETTINGS


def test_bot_token_no_cancels(tmp_path):
    cb, _, _, sessions, _ = _handlers(tmp_path)
    update, _ = _make_callback("settings:bot-token")
    asyncio.run(cb(update, _make_context()))
    update, query = _make_callback("settings:bot-token-no")
    asyncio.run(cb(update, _make_context()))
    assert sessions.get(CHAT_ID).current_screen is Screen.SETTINGS


def test_owner_ids_no_cancels(tmp_path):
    cb, _, _, sessions, _ = _handlers(tmp_path)
    update, _ = _make_callback("settings:owner-ids")
    asyncio.run(cb(update, _make_context()))
    update, query = _make_callback("settings:owner-ids-no")
    asyncio.run(cb(update, _make_context()))
    assert sessions.get(CHAT_ID).current_screen is Screen.SETTINGS


def test_text_handler_ignores_other_screens(tmp_path):
    _, text_h, _, _, router = _handlers(tmp_path)
    router.go_to(CHAT_ID, Screen.HOME)
    update, message = _make_text("123")
    assert asyncio.run(text_h(update, _make_context())) is False
    message.reply_text.assert_not_awaited()
