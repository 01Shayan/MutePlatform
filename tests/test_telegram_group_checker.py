"""Telegram Group Engine interface tests."""

from __future__ import annotations

import asyncio
import json
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

pytest.importorskip("telegram")

from mute.core.workspace import Workspace
from mute.services.workspace import ConnectionStatus
from mute.interfaces.telegram.auth import OwnerAuthorization
from mute.interfaces.telegram.handlers.group_checker import (
    make_group_checker_handler,
    make_group_checker_text_handler,
)
from mute.interfaces.telegram.router import Router
from mute.interfaces.telegram.session import Screen, SessionManager

CHAT_ID = 42
OWNER_ID = 1


class FakeWorkspaceService:
    def __init__(self, workspace: Workspace):
        self._workspace = workspace

    def workspace(self, name):
        return self._workspace if name == self._workspace.name else None

    def navigation_item(self, name):
        return SimpleNamespace(name=name, panel="PasarGuard", status=ConnectionStatus.UNKNOWN)


def _make_workspace(tmp_path) -> Workspace:
    ws = Workspace(name="Prod", integration="pasarguard", base_url="https://panel", root=tmp_path)
    ws.ensure_dirs()
    return ws


def _write_backup(ws: Workspace, name: str, users: list[dict]) -> None:
    directory = ws.backups_dir / "2026" / "07"
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / name
    path.write_text(
        json.dumps(
            {
                "metadata": {"created_at": "2026-07-15T12:00:00", "users_count": len(users)},
                "users": users,
            }
        ),
        encoding="utf-8",
    )


def _make_context():
    bot = SimpleNamespace(edit_message_text=AsyncMock(), delete_message=AsyncMock())
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


def _dispatch_callback(tmp_path, data, *, workspace=None, context=None):
    ws = workspace or _make_workspace(tmp_path)
    sessions = SessionManager()
    sessions.get(CHAT_ID).current_workspace = ws.name
    router = Router(sessions)
    handler = make_group_checker_handler(
        OwnerAuthorization(frozenset({OWNER_ID})), router, FakeWorkspaceService(ws)
    )
    update, query = _make_callback(data)
    context = context or _make_context()
    asyncio.run(handler(update, context))
    return SimpleNamespace(ws=ws, sessions=sessions, router=router, query=query, context=context)


def test_unauthorized_callback_ignored(tmp_path):
    ws = _make_workspace(tmp_path)
    sessions = SessionManager()
    sessions.get(CHAT_ID).current_workspace = ws.name
    handler = make_group_checker_handler(
        OwnerAuthorization(frozenset({OWNER_ID})), Router(sessions), FakeWorkspaceService(ws)
    )
    update, query = _make_callback("group_checker:menu")
    update.effective_user = SimpleNamespace(id=999)
    asyncio.run(handler(update, _make_context()))
    query.answer.assert_not_awaited()


def test_menu_opens(tmp_path):
    result = _dispatch_callback(tmp_path, "group_checker:menu")
    assert result.sessions.get(CHAT_ID).current_screen is Screen.GROUP_CHECKER
    text = result.query.edit_message_text.await_args.args[0]
    assert "Group Engine" in text
    assert "1. Check" in text
    assert "5. History" in text
    markup = result.query.edit_message_text.await_args.kwargs["reply_markup"]
    labels = [button.text for row in markup.inline_keyboard for button in row]
    assert labels == ["Check", "Add", "Remove", "Replace", "History", "Back"]


def test_coming_soon_operations(tmp_path):
    for operation in ("add", "remove", "replace", "history"):
        result = _dispatch_callback(tmp_path, f"group_checker:soon:{operation}")
        text = result.query.edit_message_text.await_args.args[0]
        assert "Coming soon" in text
        assert operation.capitalize() in text


def test_run_with_no_backups(tmp_path):
    result = _dispatch_callback(tmp_path, "group_checker:run")
    text = result.query.edit_message_text.await_args.args[0]
    assert "No backups" in text


def test_run_lists_backups(tmp_path):
    ws = _make_workspace(tmp_path)
    _write_backup(ws, "backup_2026-07-15_12-00-00.json", [{"username": "a", "group_ids": [1]}])
    result = _dispatch_callback(tmp_path, "group_checker:run", workspace=ws)
    assert result.sessions.get(CHAT_ID).current_screen is Screen.GROUP_CHECKER_BACKUP
    text = result.query.edit_message_text.await_args.args[0]
    assert "backup_2026-07-15_12-00-00.json" in text


def test_backup_select_shows_query(tmp_path):
    ws = _make_workspace(tmp_path)
    _write_backup(ws, "backup_2026-07-15_12-00-00.json", [{"username": "a", "group_ids": [1]}])
    result = _dispatch_callback(
        tmp_path, "group_checker:backup:backup_2026-07-15_12-00-00.json", workspace=ws
    )
    assert result.sessions.get(CHAT_ID).current_screen is Screen.GROUP_CHECKER_QUERY
    text = result.query.edit_message_text.await_args.args[0]
    assert "Required Groups" in text


def test_query_select_asks_for_group_ids(tmp_path):
    ws = _make_workspace(tmp_path)
    _write_backup(ws, "backup_2026-07-15_12-00-00.json", [{"username": "a", "group_ids": [1]}])
    result = _dispatch_callback(
        tmp_path, "group_checker:query:backup_2026-07-15_12-00-00.json", workspace=ws
    )
    assert result.sessions.get(CHAT_ID).current_screen is Screen.GROUP_CHECKER_INPUT
    assert result.sessions.get(CHAT_ID).current_action == "backup_2026-07-15_12-00-00.json"
    text = result.query.edit_message_text.await_args.args[0]
    assert "Send the required group IDs" in text


def test_text_handler_opens_confirmation(tmp_path):
    ws = _make_workspace(tmp_path)
    _write_backup(
        ws,
        "backup_2026-07-15_12-00-00.json",
        [{"username": "bob", "group_ids": [1]}],
    )
    sessions = SessionManager()
    sessions.get(CHAT_ID).current_workspace = ws.name
    router = Router(sessions)
    router.group_checker_input(CHAT_ID, "backup_2026-07-15_12-00-00.json")
    router.remember_message(CHAT_ID, 555)

    handler = make_group_checker_text_handler(
        OwnerAuthorization(frozenset({OWNER_ID})), router, FakeWorkspaceService(ws)
    )
    reply = AsyncMock()
    update = SimpleNamespace(
        effective_user=SimpleNamespace(id=OWNER_ID),
        effective_chat=SimpleNamespace(id=CHAT_ID),
        effective_message=SimpleNamespace(text="1, 3", reply_text=reply, message_id=777),
        callback_query=None,
    )
    context = _make_context()
    asyncio.run(handler(update, context))

    assert sessions.get(CHAT_ID).current_screen is Screen.GROUP_CHECKER_CONFIRM
    context.bot.edit_message_text.assert_awaited()
    text = context.bot.edit_message_text.await_args.kwargs["text"]
    assert "Required Groups: 1, 3" in text


def test_confirm_runs_query_and_shows_result(tmp_path):
    ws = _make_workspace(tmp_path)
    _write_backup(
        ws,
        "backup_2026-07-15_12-00-00.json",
        [
            {"username": "alice", "group_ids": [1, 3]},
            {"username": "bob", "group_ids": [1]},
        ],
    )
    sessions = SessionManager()
    sessions.get(CHAT_ID).current_workspace = ws.name
    sessions.get(CHAT_ID).current_action = "backup_2026-07-15_12-00-00.json|1,3"
    router = Router(sessions)
    handler = make_group_checker_handler(
        OwnerAuthorization(frozenset({OWNER_ID})), router, FakeWorkspaceService(ws)
    )
    update, query = _make_callback("group_checker:confirm")
    context = _make_context()
    asyncio.run(handler(update, context))

    assert sessions.get(CHAT_ID).current_screen is Screen.GROUP_CHECKER_RESULT
    texts = [call.kwargs.get("text") or (call.args[0] if call.args else "") for call in context.bot.edit_message_text.await_args_list]
    joined = "\n".join(texts)
    assert "Query completed" in joined or any("Matching Users: 1" in t for t in texts)
    assert any("bob" in (t or "") for t in texts)

    history = list(ws.history_dir.glob("*_group_checker.json"))
    assert len(history) == 1
