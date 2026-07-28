"""Telegram Bulk Operations / Group Manager smoke tests."""

from __future__ import annotations

import asyncio
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

pytest.importorskip("telegram")

from mute.core.workspace import Workspace
from mute.services.bulk_operations.group_manager import GroupManagerApplicationService
from mute.services.bulk_operations.group_manager.catalog import GroupCatalog, GroupInfo
from mute.services.bulk_operations.group_manager.snapshot import GroupSnapshot, SnapshotUser
from mute.services.workspace import ConnectionStatus
from mute.interfaces.telegram.auth import OwnerAuthorization
from mute.interfaces.telegram.handlers.group_manager import make_bulk_ops_handler
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


def _workspace(tmp_path) -> Workspace:
    ws = Workspace(name="Prod", integration="pasarguard", base_url="https://panel", root=tmp_path)
    ws.ensure_dirs()
    return ws


def _make_context():
    return SimpleNamespace(
        bot=SimpleNamespace(edit_message_text=AsyncMock(), delete_message=AsyncMock(), send_document=AsyncMock())
    )


def _callback(data: str):
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


def test_bulk_ops_menu(tmp_path):
    ws = _workspace(tmp_path)
    sessions = SessionManager()
    sessions.get(CHAT_ID).current_workspace = ws.name
    handler = make_bulk_ops_handler(
        OwnerAuthorization(frozenset({OWNER_ID})),
        Router(sessions),
        FakeWorkspaceService(ws),
    )
    update, query = _callback("bulk:menu")
    asyncio.run(handler(update, _make_context()))
    assert sessions.get(CHAT_ID).current_screen is Screen.BULK_OPS
    assert "Bulk Operations" in query.edit_message_text.await_args.args[0]


def test_group_manager_menu_after_snapshot(tmp_path, monkeypatch):
    ws = _workspace(tmp_path)
    service = GroupManagerApplicationService()
    snapshot = GroupSnapshot(
        users=(SnapshotUser("alice", (1,)),),
        loaded_at=datetime(2026, 7, 28),
    )
    catalog = GroupCatalog(groups=(GroupInfo(1, "a"),))

    def fake_ensure(workspace, *, session_key="default", client=None):
        from mute.services.bulk_operations.group_manager.session import GroupManagerSession

        session = GroupManagerSession(
            workspace_name=workspace.name, catalog=catalog, snapshot=snapshot
        )
        service._sessions[session_key] = session
        return session

    monkeypatch.setattr(service, "ensure_session", fake_ensure)
    sessions = SessionManager()
    sessions.get(CHAT_ID).current_workspace = ws.name
    handler = make_bulk_ops_handler(
        OwnerAuthorization(frozenset({OWNER_ID})),
        Router(sessions),
        FakeWorkspaceService(ws),
        service,
    )
    update, query = _callback("bulk:group_manager")
    asyncio.run(handler(update, _make_context()))
    assert sessions.get(CHAT_ID).current_screen is Screen.GROUP_MANAGER
    text = query.edit_message_text.await_args_list[-1].args[0]
    assert "Group Manager" in text
    assert "Matched Users" in text
    markup = query.edit_message_text.await_args_list[-1].kwargs.get("reply_markup")
    labels = [btn.text for row in markup.inline_keyboard for btn in row]
    assert any("Select Target Users" in label for label in labels)
    assert any("Refresh Snapshot" in label for label in labels)
