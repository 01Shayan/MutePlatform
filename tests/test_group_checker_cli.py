"""CLI Group Checker screen flow tests (no interactive prompts left unmocked)."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace

from mute.cli.screens import group_checker as screen
from mute.core.workspace import Workspace
from mute.services.group_checker import GroupCheckerApplicationService
from mute.services.group_checker.models import GroupCheckerResult, GroupCheckerUserResult


def _workspace(tmp_path: Path) -> Workspace:
    ws = Workspace(name="Prod", integration="pasarguard", base_url="https://panel", root=tmp_path)
    ws.ensure_dirs()
    return ws


def _write_backup(ws: Workspace, users: list[dict]) -> str:
    directory = ws.backups_dir / "2026" / "07"
    directory.mkdir(parents=True, exist_ok=True)
    name = "backup_2026-07-15_12-00-00.json"
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
    return name


def test_cli_run_query_flow(tmp_path, monkeypatch):
    ws = _workspace(tmp_path)
    _write_backup(
        ws,
        [
            {"username": "alice", "group_ids": [1, 3]},
            {"username": "bob", "group_ids": [1]},
        ],
    )

    shown = {}
    monkeypatch.setattr(screen, "_show_result", lambda result: shown.setdefault("result", result))
    monkeypatch.setattr(screen.theme, "page", lambda *a, **k: None)
    monkeypatch.setattr(screen.theme, "clear", lambda: None)
    monkeypatch.setattr(screen.theme, "pause", lambda *a, **k: None)
    monkeypatch.setattr(screen.theme, "notify_info", lambda *a, **k: None)
    monkeypatch.setattr(screen.console, "print", lambda *a, **k: None)

    class _Status:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

    monkeypatch.setattr(screen.console, "status", lambda *a, **k: _Status())
    monkeypatch.setattr(screen.Confirm, "ask", staticmethod(lambda *a, **k: True))

    # Menu: Run Query → Back. Inside flow: backup #1, query Required Groups, group IDs.
    prompts = iter(
        [
            "1",  # menu → Run Query
            "1",  # select backup
            "1",  # Required Groups
            "1, 3",  # group IDs
            "0",  # menu → Back
        ]
    )
    monkeypatch.setattr(screen.Prompt, "ask", staticmethod(lambda *a, **k: next(prompts)))

    screen.run(ws)

    assert shown["result"].matching_users == 1
    assert shown["result"].users[0].username == "bob"
    assert list(ws.history_dir.glob("*_group_checker.json"))


def test_cli_select_backup_returns_none_when_empty(tmp_path, monkeypatch):
    ws = _workspace(tmp_path)
    monkeypatch.setattr(screen.theme, "page", lambda *a, **k: None)
    monkeypatch.setattr(screen.theme, "pause", lambda *a, **k: None)
    assert screen._select_backup(GroupCheckerApplicationService(), ws) is None


def test_cli_prompt_group_ids_invalid(monkeypatch):
    monkeypatch.setattr(screen.Prompt, "ask", staticmethod(lambda *a, **k: "nope"))
    monkeypatch.setattr(screen.theme, "notify_warning", lambda *a, **k: None)
    monkeypatch.setattr(screen.theme, "pause", lambda *a, **k: None)
    monkeypatch.setattr(screen.console, "print", lambda *a, **k: None)
    assert screen._prompt_group_ids() is None


def test_cli_show_result_with_and_without_matches(monkeypatch):
    monkeypatch.setattr(screen.theme, "page", lambda *a, **k: None)
    monkeypatch.setattr(screen.theme, "pause", lambda *a, **k: None)

    empty = GroupCheckerResult(
        workspace="P",
        backup_name="b.json",
        backup_created_at=datetime(2026, 7, 15),
        query_type="required_groups",
        query_label="Required Groups",
        required_group_ids=(1,),
        total_users=1,
        matching_users=0,
        users=(),
        duration_seconds=0.1,
    )
    screen._show_result(empty)

    filled = GroupCheckerResult(
        workspace="P",
        backup_name="b.json",
        backup_created_at=datetime(2026, 7, 15),
        query_type="required_groups",
        query_label="Required Groups",
        required_group_ids=(1, 3),
        total_users=2,
        matching_users=1,
        users=(GroupCheckerUserResult("bob", (1,), (3,)),),
        duration_seconds=0.2,
    )
    screen._show_result(filled)
