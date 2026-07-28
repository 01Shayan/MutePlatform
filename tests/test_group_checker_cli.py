"""CLI Group Manager screen flow tests (no interactive prompts left unmocked)."""

from __future__ import annotations

import json
from pathlib import Path

from mute.cli.screens import group_manager as screen
from mute.core.workspace import Workspace
from mute.services.bulk_operations.group_manager import GroupManagerApplicationService


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


def test_cli_check_flow_builds_working_set(tmp_path, monkeypatch):
    ws = _workspace(tmp_path)
    _write_backup(
        ws,
        [
            {"username": "alice", "group_ids": [1, 3]},
            {"username": "bob", "group_ids": [1]},
        ],
    )

    shown = {}
    monkeypatch.setattr(
        screen,
        "_show_working_set_and_actions",
        lambda service, working_set: shown.setdefault("working_set", working_set),
    )
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

    prompts = iter(
        [
            "1",  # Check Group IDs
            "1",  # select backup
            "1",  # Required Groups
            "1, 3",  # group IDs
            "0",  # Group Manager → Back
        ]
    )
    monkeypatch.setattr(screen.Prompt, "ask", staticmethod(lambda *a, **k: next(prompts)))

    screen.run(ws)

    assert shown["working_set"].matched_count == 1
    assert shown["working_set"].matched_users[0].username == "bob"
    assert shown["working_set"].unmatched_count == 1
    assert list(ws.history_dir.glob("*_group_checker.json"))


def test_cli_select_backup_returns_none_when_empty(tmp_path, monkeypatch):
    ws = _workspace(tmp_path)
    monkeypatch.setattr(screen.theme, "page", lambda *a, **k: None)
    monkeypatch.setattr(screen.theme, "pause", lambda *a, **k: None)
    assert screen._select_backup(GroupManagerApplicationService(), ws) is None


def test_cli_prompt_group_ids_invalid(monkeypatch):
    monkeypatch.setattr(screen.Prompt, "ask", staticmethod(lambda *a, **k: "nope"))
    monkeypatch.setattr(screen.theme, "notify_warning", lambda *a, **k: None)
    monkeypatch.setattr(screen.theme, "pause", lambda *a, **k: None)
    monkeypatch.setattr(screen.console, "print", lambda *a, **k: None)
    assert screen._prompt_group_ids() is None
