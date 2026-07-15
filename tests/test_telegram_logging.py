import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

pytest.importorskip("telegram")

from mute.core import logging as core_logging
from mute.core.workspace import Workspace
from mute.interfaces.telegram.auth import OwnerAuthorization
from mute.interfaces.telegram.handlers.backup import make_backup_handler
from mute.interfaces.telegram.router import Router
from mute.interfaces.telegram.session import SessionManager

CHAT_ID = 42
OWNER_ID = 1


class FakeWorkspaceService:
    def __init__(self, workspace):
        self._workspace = workspace

    def workspace(self, name):
        return self._workspace if name == self._workspace.name else None

    def navigation_item(self, name):
        return SimpleNamespace(name=name, panel="PasarGuard")


def _make_update(data):
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
    )
    return update, query


def test_backup_handler_routes_logging_into_workspace(tmp_path, monkeypatch):
    # Start from a clean logging state (no active workspace directory).
    monkeypatch.setattr(core_logging, "_current_dir", None)

    ws = Workspace(name="Prod", integration="pasarguard", base_url="https://panel", root=tmp_path)
    ws.ensure_dirs()

    sessions = SessionManager()
    sessions.get(CHAT_ID).current_workspace = ws.name
    router = Router(sessions)
    handler = make_backup_handler(
        OwnerAuthorization(frozenset({OWNER_ID})), router, FakeWorkspaceService(ws)
    )

    update, _ = _make_update("backup:menu")
    asyncio.run(handler(update, SimpleNamespace(bot=SimpleNamespace(edit_message_text=AsyncMock()))))

    # Resolving the workspace pointed the shared logging channels at its logs folder,
    # exactly like the CLI's open_workspace — no logging logic is duplicated in the handler.
    assert core_logging._current_dir == ws.logs_dir

    core_logging.get_logger("backup").info("telegram backup log line")
    backup_log = ws.logs_dir / "backup.log"
    assert backup_log.exists()
    assert "telegram backup log line" in backup_log.read_text(encoding="utf-8")
