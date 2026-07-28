"""Group Manager / Working Set infrastructure tests."""

from __future__ import annotations

import json

import pytest

from mute.core.workspace import Workspace
from mute.services.bulk_operations.group_manager import (
    GroupManagerApplicationService,
    GroupManagerError,
)
from mute.services.group_checker.models import GroupQueryDescriptor, GroupQueryType


def _workspace(tmp_path) -> Workspace:
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


def test_check_builds_working_set(tmp_path):
    ws = _workspace(tmp_path)
    _write_backup(
        ws,
        "backup_2026-07-15_12-00-00.json",
        [
            {"username": "alice", "group_ids": [1, 3]},
            {"username": "bob", "group_ids": [1]},
            {"username": "carol", "group_ids": [1, 3]},
        ],
    )
    service = GroupManagerApplicationService()
    service.begin_session(ws)
    working_set = service.run_check(
        ws,
        "backup_2026-07-15_12-00-00.json",
        GroupQueryDescriptor(GroupQueryType.REQUIRED_GROUPS, (1, 3)),
    )
    assert working_set.matched_count == 1
    assert working_set.matched_users[0].username == "bob"
    assert working_set.unmatched_count == 2
    assert {u.username for u in working_set.unmatched_users} == {"alice", "carol"}
    assert working_set.required_group_ids == (1, 3)
    assert service.working_set() is working_set


def test_actions_require_working_set(tmp_path):
    ws = _workspace(tmp_path)
    service = GroupManagerApplicationService()
    service.begin_session(ws)
    with pytest.raises(GroupManagerError, match="Check Group IDs"):
        service.execute_action(ws, "add", {"group_ids": [5]})


def test_actions_are_coming_soon_after_check(tmp_path):
    ws = _workspace(tmp_path)
    _write_backup(
        ws,
        "backup_2026-07-15_12-00-00.json",
        [{"username": "bob", "group_ids": [1]}],
    )
    service = GroupManagerApplicationService()
    service.begin_session(ws)
    service.run_check(
        ws,
        "backup_2026-07-15_12-00-00.json",
        GroupQueryDescriptor(GroupQueryType.REQUIRED_GROUPS, (1, 3)),
    )
    labels = [item.label for item in service.list_actions()]
    assert labels == ["Add Group IDs", "Remove Group IDs", "Replace Group IDs"]
    assert all(not item.available for item in service.list_actions())
    with pytest.raises(GroupManagerError, match="coming soon"):
        service.execute_action(ws, "add", {"group_ids": [5]})


def test_leave_session_clears_working_set(tmp_path):
    ws = _workspace(tmp_path)
    _write_backup(
        ws,
        "backup_2026-07-15_12-00-00.json",
        [{"username": "bob", "group_ids": [1]}],
    )
    service = GroupManagerApplicationService()
    service.begin_session(ws)
    service.run_check(
        ws,
        "backup_2026-07-15_12-00-00.json",
        GroupQueryDescriptor(GroupQueryType.REQUIRED_GROUPS, (1, 3)),
    )
    service.leave_session()
    assert service.working_set() is None
