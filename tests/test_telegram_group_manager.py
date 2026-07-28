"""Telegram Bulk Operations / Group Manager interface tests."""

from __future__ import annotations

import asyncio
import json
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

pytest.importorskip("telegram")

from mute.core.workspace import Workspace
from mute.services.bulk_operations.group_manager import GroupManagerApplicationService
from mute.services.workspace import ConnectionStatus
from mute.interfaces.telegram.auth import OwnerAuthorization
from mute.interfaces.telegram.handlers.group_manager import (
    make_bulk_ops_handler,
    make_group_manager_text_handler,
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
    (directory / name).write_text(
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


def _dispatch(tmp_path, data, *, workspace=None, service=None):
    ws = workspace or _make_workspace(tmp_path)
    sessions = SessionManager()
    sessions.get(CHAT_ID).current_workspace = ws.name
    router = Router(sessions)
    service = service or GroupManagerApplicationService()
    handler = make_bulk_ops_handler(
        OwnerAuthorization(frozenset({OWNER_ID})), router, FakeWorkspaceService(ws), service
    )
    update, query = _make_callback(data)
    asyncio.run(handler(update, _make_context()))
    return SimpleNamespace(ws=ws, sessions=sessions, router=router, query=query, service=service)


def test_bulk_ops_menu(tmp_path):
    result = _dispatch(tmp_path, "bulk:menu")
    assert result.sessions.get(CHAT_ID).current_screen is Screen.BULK_OPS
    text = result.query.edit_message_text.await_args.args[0]
    assert "Bulk Operations" in text
    assert "Group Manager" in text


def test_group_manager_menu(tmp_path):
    result = _dispatch(tmp_path, "bulk:group_manager")
    assert result.sessions.get(CHAT_ID).current_screen is Screen.GROUP_MANAGER
    text = result.query.edit_message_text.await_args.args[0]
    assert "Group Manager" in text
    assert "Check Group IDs" in text
    markup = result.query.edit_message_text.await_args.kwargs["reply_markup"]
    labels = [button.text for row in markup.inline_keyboard for button in row]
    assert labels == ["Check Group IDs", "Back"]


def test_check_builds_working_set_and_shows_actions(tmp_path):
    ws = _make_workspace(tmp_path)
    _write_backup(
        ws,
        "backup_2026-07-15_12-00-00.json",
        [
            {"username": "alice", "group_ids": [1, 3]},
            {"username": "bob", "group_ids": [1]},
        ],
    )
    service = GroupManagerApplicationService()
    sessions = SessionManager()
    sessions.get(CHAT_ID).current_workspace = ws.name
    sessions.get(CHAT_ID).current_action = "backup_2026-07-15_12-00-00.json|1,3"
    router = Router(sessions)
    handler = make_bulk_ops_handler(
        OwnerAuthorization(frozenset({OWNER_ID})), router, FakeWorkspaceService(ws), service
    )
    update, query = _make_callback("gm:confirm")
    context = _make_context()
    asyncio.run(handler(update, context))

    working_set = service.working_set(session_key=str(CHAT_ID))
    assert working_set is not None
    assert working_set.matched_count == 1
    assert working_set.matched_users[0].username == "bob"
    assert sessions.get(CHAT_ID).current_screen is Screen.GM_WORKING_SET
    texts = [
        call.kwargs.get("text") or (call.args[0] if call.args else "")
        for call in context.bot.edit_message_text.await_args_list
    ]
    joined = "\n".join(texts)
    assert "Matched Users: 1" in joined or "bob" in joined
    history = list(ws.history_dir.glob("*_group_checker.json"))
    assert len(history) == 1


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
    router.gm_check_input(CHAT_ID, "backup_2026-07-15_12-00-00.json")
    router.remember_message(CHAT_ID, 555)
    handler = make_group_manager_text_handler(
        OwnerAuthorization(frozenset({OWNER_ID})),
        router,
        FakeWorkspaceService(ws),
        GroupManagerApplicationService(),
    )
    update = SimpleNamespace(
        effective_user=SimpleNamespace(id=OWNER_ID),
        effective_chat=SimpleNamespace(id=CHAT_ID),
        effective_message=SimpleNamespace(text="1, 3", reply_text=AsyncMock(), message_id=777),
        callback_query=None,
    )
    context = _make_context()
    asyncio.run(handler(update, context))
    assert sessions.get(CHAT_ID).current_screen is Screen.GM_CHECK_CONFIRM
    text = context.bot.edit_message_text.await_args.kwargs["text"]
    assert "Required Groups: 1, 3" in text


def test_leave_dashboard_clears_session(tmp_path):
    ws = _make_workspace(tmp_path)
    service = GroupManagerApplicationService()
    service.begin_session(ws, session_key=str(CHAT_ID))
    result = _dispatch(tmp_path, "bulk:dashboard", workspace=ws, service=service)
    assert service.session(session_key=str(CHAT_ID)) is None
    assert result.sessions.get(CHAT_ID).current_screen is Screen.DASHBOARD
