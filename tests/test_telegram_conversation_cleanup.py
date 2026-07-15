"""Temporary Telegram conversation cleanup."""

from __future__ import annotations

import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

pytest.importorskip("telegram")

from mute.core.workspace import WorkspaceStore
from mute.interfaces.telegram.auth import OwnerAuthorization
from mute.interfaces.telegram.conversation import (
    begin_temporary,
    cleanup_temporary,
    track_temporary,
)
from mute.interfaces.telegram.handlers.group_checker import (
    make_group_checker_handler,
    make_group_checker_text_handler,
)
from mute.interfaces.telegram.handlers.workspace import (
    make_workspace_handler,
    make_workspace_text_handler,
)
from mute.interfaces.telegram.router import Router
from mute.interfaces.telegram.session import Screen, SessionManager
from mute.services.workspace import WorkspaceApplicationService

CHAT_ID = 42
OWNER_ID = 1


def _service(tmp_path) -> WorkspaceApplicationService:
    return WorkspaceApplicationService(
        WorkspaceStore(root=tmp_path / "workspaces", registry_path=tmp_path / "config" / "workspaces.json")
    )


def _make_context():
    bot = SimpleNamespace(
        edit_message_text=AsyncMock(),
        delete_message=AsyncMock(),
    )
    return SimpleNamespace(bot=bot, application=SimpleNamespace(bot_data={}))


def _callback(data: str):
    query = SimpleNamespace(
        data=data,
        answer=AsyncMock(),
        edit_message_text=AsyncMock(),
        message=SimpleNamespace(message_id=100),
    )
    update = SimpleNamespace(
        effective_user=SimpleNamespace(id=OWNER_ID),
        effective_chat=SimpleNamespace(id=CHAT_ID),
        callback_query=query,
        effective_message=None,
    )
    return update, query


def _text(text: str, message_id: int = 200):
    message = SimpleNamespace(text=text, reply_text=AsyncMock(), message_id=message_id)
    update = SimpleNamespace(
        effective_user=SimpleNamespace(id=OWNER_ID),
        effective_chat=SimpleNamespace(id=CHAT_ID),
        effective_message=message,
        callback_query=None,
    )
    return update, message


def test_track_and_cleanup_keeps_final_message():
    sessions = SessionManager()
    router = Router(sessions)
    begin_temporary(router, CHAT_ID)
    router.remember_message(CHAT_ID, 100)
    track_temporary(router, CHAT_ID, 201)
    track_temporary(router, CHAT_ID, 202)
    track_temporary(router, CHAT_ID, 100)  # UI message accidentally tracked — keep wins

    bot = SimpleNamespace(delete_message=AsyncMock())
    asyncio.run(cleanup_temporary(bot, router, CHAT_ID, keep=100))

    deleted = {call.kwargs["message_id"] for call in bot.delete_message.await_args_list}
    assert deleted == {201, 202}
    assert router.session(CHAT_ID).temporary_messages == []
    assert router.session(CHAT_ID).last_message_id == 100


def test_cleanup_continues_when_delete_raises():
    sessions = SessionManager()
    router = Router(sessions)
    router.remember_message(CHAT_ID, 100)
    track_temporary(router, CHAT_ID, 201)
    track_temporary(router, CHAT_ID, 202)
    track_temporary(router, CHAT_ID, 203)

    attempted: list[int] = []

    async def flaky_delete(*, chat_id, message_id):
        attempted.append(message_id)
        if message_id == 201:
            raise RuntimeError("network down")
        if message_id == 202:
            from telegram.error import Forbidden

            raise Forbidden("not enough rights")
        # 203 succeeds

    bot = SimpleNamespace(delete_message=AsyncMock(side_effect=flaky_delete))
    asyncio.run(cleanup_temporary(bot, router, CHAT_ID, keep=100))

    assert attempted == [201, 202, 203]
    assert router.session(CHAT_ID).temporary_messages == []


def test_workspace_create_succeeds_when_cleanup_delete_fails(tmp_path):
    service = _service(tmp_path)
    sessions = SessionManager()
    router = Router(sessions)
    auth = OwnerAuthorization(frozenset({OWNER_ID}))
    cb = make_workspace_handler(auth, router, service)
    text_h = make_workspace_text_handler(auth, router, service)
    context = _make_context()
    context.bot.delete_message = AsyncMock(side_effect=RuntimeError("telegram unavailable"))

    update, _ = _callback("ws:add")
    asyncio.run(cb(update, context))
    update, _ = _text("Alpha", message_id=201)
    asyncio.run(text_h(update, context))

    sessions.get(CHAT_ID).draft.update(
        {
            "integration": "pasarguard",
            "integration_label": "PasarGuard",
            "base_url": "https://panel",
            "auth": "password",
            "username": "a",
            "password": "b",
            "verify_ssl": True,
            "probe_ok": True,
        }
    )
    router.go_to(CHAT_ID, Screen.WS_ADD_CONFIRM)
    update, query = _callback("ws:confirm-create")
    asyncio.run(cb(update, context))

    assert service.workspace("Alpha") is not None
    assert sessions.get(CHAT_ID).current_screen is Screen.DASHBOARD
    assert "created successfully" in query.edit_message_text.await_args.args[0]


def test_workspace_create_cleans_user_replies(tmp_path):
    service = _service(tmp_path)
    sessions = SessionManager()
    router = Router(sessions)
    auth = OwnerAuthorization(frozenset({OWNER_ID}))
    cb = make_workspace_handler(auth, router, service)
    text_h = make_workspace_text_handler(auth, router, service)
    context = _make_context()

    update, _ = _callback("ws:add")
    asyncio.run(cb(update, context))
    assert sessions.get(CHAT_ID).temporary_messages == []
    assert sessions.get(CHAT_ID).last_message_id == 100

    update, _ = _text("Alpha", message_id=201)
    asyncio.run(text_h(update, context))
    assert 201 in sessions.get(CHAT_ID).temporary_messages

    sessions.get(CHAT_ID).draft.update(
        {
            "integration": "pasarguard",
            "integration_label": "PasarGuard",
            "base_url": "https://panel",
            "auth": "password",
            "username": "a",
            "password": "b",
            "verify_ssl": True,
            "probe_ok": True,
        }
    )
    router.go_to(CHAT_ID, Screen.WS_ADD_CONFIRM)
    update, query = _callback("ws:confirm-create")
    asyncio.run(cb(update, context))

    assert sessions.get(CHAT_ID).current_screen is Screen.DASHBOARD
    assert sessions.get(CHAT_ID).temporary_messages == []
    context.bot.delete_message.assert_awaited()
    deleted = {call.kwargs["message_id"] for call in context.bot.delete_message.await_args_list}
    assert 201 in deleted
    assert 100 not in deleted  # final dashboard message kept
    query.edit_message_text.assert_awaited()
    assert "created successfully" in query.edit_message_text.await_args.args[0]


def test_workspace_cancel_cleans_temporary(tmp_path):
    service = _service(tmp_path)
    sessions = SessionManager()
    router = Router(sessions)
    auth = OwnerAuthorization(frozenset({OWNER_ID}))
    cb = make_workspace_handler(auth, router, service)
    text_h = make_workspace_text_handler(auth, router, service)
    context = _make_context()

    update, _ = _callback("ws:add")
    asyncio.run(cb(update, context))
    sessions.get(CHAT_ID).last_message_id = 100
    update, _ = _text("TempName", message_id=301)
    asyncio.run(text_h(update, context))
    assert 301 in sessions.get(CHAT_ID).temporary_messages

    update, query = _callback("ws:cancel")
    asyncio.run(cb(update, context))
    assert sessions.get(CHAT_ID).current_screen is Screen.WORKSPACES
    assert sessions.get(CHAT_ID).temporary_messages == []
    deleted = {call.kwargs["message_id"] for call in context.bot.delete_message.await_args_list}
    assert 301 in deleted
    assert "My Workspaces" in query.edit_message_text.await_args.args[0]


def test_workspace_edit_success_cleans_temporary(tmp_path):
    service = _service(tmp_path)
    service.create(
        name="Prod",
        integration="pasarguard",
        connection={"base_url": "https://old", "username": "a", "password": "b"},
    )
    sessions = SessionManager()
    sessions.get(CHAT_ID).current_workspace = "Prod"
    router = Router(sessions)
    auth = OwnerAuthorization(frozenset({OWNER_ID}))
    cb = make_workspace_handler(auth, router, service)
    text_h = make_workspace_text_handler(auth, router, service)
    context = _make_context()

    update, _ = _callback("ws:edit")
    asyncio.run(cb(update, context))
    sessions.get(CHAT_ID).last_message_id = 100
    update, _ = _text("Prod2", message_id=401)
    asyncio.run(text_h(update, context))

    sessions.get(CHAT_ID).draft.update(
        {
            "base_url": "https://new",
            "auth": "password",
            "username": "a",
            "password": "b",
            "verify_ssl": True,
            "probe_ok": False,
        }
    )
    router.go_to(CHAT_ID, Screen.WS_EDIT_CONFIRM)
    update, query = _callback("ws:confirm-update")
    asyncio.run(cb(update, context))

    assert sessions.get(CHAT_ID).current_workspace == "Prod2"
    assert sessions.get(CHAT_ID).temporary_messages == []
    deleted = {call.kwargs["message_id"] for call in context.bot.delete_message.await_args_list}
    assert 401 in deleted
    assert "updated successfully" in query.edit_message_text.await_args.args[0]


def test_group_checker_input_cleanup_on_result(tmp_path):
    service = _service(tmp_path)
    ws = service.create(
        name="Prod",
        integration="pasarguard",
        connection={"base_url": "https://panel"},
    )
    # Minimal backup for list/run path is not needed — we jump to text input.
    sessions = SessionManager()
    sessions.get(CHAT_ID).current_workspace = "Prod"
    router = Router(sessions)
    auth = OwnerAuthorization(frozenset({OWNER_ID}))
    text_h = make_group_checker_text_handler(auth, router, service)
    cb = make_group_checker_handler(auth, router, service)
    context = _make_context()

    begin_temporary(router, CHAT_ID)
    router.remember_message(CHAT_ID, 100)
    router.group_checker_input(CHAT_ID, "backup_2026-07-15_12-00-00.json")
    sessions.get(CHAT_ID).current_action = "backup_2026-07-15_12-00-00.json"

    update, message = _text("1,3", message_id=501)
    # list_backups will be empty — users=0 still ok for confirmation
    asyncio.run(text_h(update, context))
    assert 501 in sessions.get(CHAT_ID).temporary_messages
    assert sessions.get(CHAT_ID).current_screen is Screen.GROUP_CHECKER_CONFIRM

    # Cancel back via run should clean temporary replies.
    update, _ = _callback("group_checker:run")
    # Need a backup so run doesn't just show empty — empty is fine
    from pathlib import Path
    import json

    directory = ws.backups_dir / "2026" / "07"
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "backup_2026-07-15_12-00-00.json").write_text(
        json.dumps({"metadata": {"created_at": "2026-07-15T12:00:00", "users_count": 0}, "users": []}),
        encoding="utf-8",
    )
    asyncio.run(cb(update, context))
    assert sessions.get(CHAT_ID).temporary_messages == []
    deleted = {call.kwargs["message_id"] for call in context.bot.delete_message.await_args_list}
    assert 501 in deleted


def test_begin_temporary_resets_list():
    sessions = SessionManager()
    router = Router(sessions)
    track_temporary(router, CHAT_ID, 1)
    track_temporary(router, CHAT_ID, 2)
    begin_temporary(router, CHAT_ID)
    assert sessions.get(CHAT_ID).temporary_messages == []
