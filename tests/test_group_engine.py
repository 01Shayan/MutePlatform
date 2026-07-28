"""Group Engine workflow infrastructure tests."""

from __future__ import annotations

import json
from typing import Any, Mapping, Sequence

import pytest

from mute.core.workspace import Workspace
from mute.services.group_engine import (
    GroupEngineApplicationService,
    GroupEngineError,
    GroupOperation,
    OperationSummary,
    PreviewPlan,
    SelectedUser,
    WorkflowStage,
)


def _workspace(tmp_path) -> Workspace:
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


class _FakeAdd(GroupOperation):
    id = "add"
    label = "Add"
    description = "test add"
    available = True

    def validate_parameters(
        self, parameters: Mapping[str, Any], users: Sequence[SelectedUser]
    ) -> None:
        if "group_ids" not in parameters:
            raise ValueError("group_ids required")

    def build_preview(
        self, users: Sequence[SelectedUser], parameters: Mapping[str, Any]
    ) -> PreviewPlan:
        return PreviewPlan(
            operation_id=self.id,
            operation_label=self.label,
            user_count=len(users),
            usernames=tuple(u.username for u in users),
            parameters=dict(parameters),
            lines=("Will add groups",),
        )

    def execute(
        self,
        users: Sequence[SelectedUser],
        parameters: Mapping[str, Any],
        *,
        workspace: Workspace,
    ) -> OperationSummary:
        return OperationSummary(
            operation_id=self.id,
            operation_label=self.label,
            user_count=len(users),
            usernames=tuple(u.username for u in users),
            parameters=dict(parameters),
            message="Added",
        )


def test_session_lifecycle(tmp_path):
    ws = _workspace(tmp_path)
    service = GroupEngineApplicationService()
    session = service.begin_session(ws)
    assert session.workspace_name == "Prod"
    assert service.stage() is WorkflowStage.SELECT_USERS
    service.leave_session()
    assert service.session() is None
    with pytest.raises(GroupEngineError):
        service.require_session()


def test_user_selection_persists_across_operations(tmp_path):
    ws = _workspace(tmp_path)
    _write_backup(
        ws,
        "backup_2026-07-15_12-00-00.json",
        [
            {"username": "alice", "group_ids": [1]},
            {"username": "bob", "group_ids": [2]},
        ],
    )
    service = GroupEngineApplicationService()
    service.register_operation(_FakeAdd())
    service.begin_session(ws)
    service.select_users_by_username(
        ws, "backup_2026-07-15_12-00-00.json", ["alice", "bob"]
    )
    assert service.require_session().selected_count == 2

    service.select_operation("add")
    service.configure({"group_ids": [3]})
    preview = service.build_preview()
    assert preview.user_count == 2
    summary = service.execute(ws)
    assert summary.message == "Added"
    # Users remain for the next operation.
    assert service.require_session().selected_count == 2
    assert service.require_session().operation_id is None
    assert service.stage() is WorkflowStage.CHOOSE_OPERATION


def test_stub_operations_are_coming_soon(tmp_path):
    ws = _workspace(tmp_path)
    service = GroupEngineApplicationService()
    service.begin_session(ws)
    service.set_selected_users([SelectedUser(username="alice", group_ids=(1,))])
    ops = {item.id: item for item in service.list_operations()}
    assert ops["add"].available is False
    with pytest.raises(GroupEngineError, match="coming soon"):
        service.select_operation("add")


def test_preview_required_before_execute(tmp_path):
    ws = _workspace(tmp_path)
    service = GroupEngineApplicationService()
    service.register_operation(_FakeAdd())
    service.begin_session(ws)
    service.set_selected_users([SelectedUser(username="alice")])
    service.select_operation("add")
    service.configure({"group_ids": [1]})
    with pytest.raises(GroupEngineError, match="preview"):
        service.execute(ws)


def test_select_all_from_backup(tmp_path):
    ws = _workspace(tmp_path)
    _write_backup(
        ws,
        "backup_2026-07-15_12-00-00.json",
        [{"username": "a", "group_ids": []}, {"username": "b", "group_ids": [1]}],
    )
    service = GroupEngineApplicationService()
    service.begin_session(ws)
    session = service.select_all_users_from_backup(ws, "backup_2026-07-15_12-00-00.json")
    assert session.selected_count == 2
    assert session.backup_name == "backup_2026-07-15_12-00-00.json"


def test_session_keys_are_isolated(tmp_path):
    ws = _workspace(tmp_path)
    service = GroupEngineApplicationService()
    service.begin_session(ws, session_key="cli")
    service.begin_session(ws, session_key="42")
    service.set_selected_users(
        [SelectedUser(username="alice")], session_key="cli"
    )
    assert service.session(session_key="42").selected_count == 0
    assert service.session(session_key="cli").selected_count == 1
    service.leave_session(session_key="cli")
    assert service.session(session_key="42") is not None
