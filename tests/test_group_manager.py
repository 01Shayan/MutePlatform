"""Group Manager architecture v1.2 unit tests."""

from __future__ import annotations

from datetime import datetime
from types import SimpleNamespace

import pytest

from mute.core.workspace import Workspace
from mute.services.bulk_operations.group_manager import (
    GroupManagerApplicationService,
    GroupManagerError,
    GroupQuery,
    MatchMode,
    format_available_groups,
    format_home_status,
    format_query_preview,
    format_review_screen,
)
from mute.services.bulk_operations.group_manager.catalog import GroupCatalog, GroupInfo
from mute.services.bulk_operations.group_manager.copy import MENU_FILTER_USERS
from mute.services.bulk_operations.group_manager.target_rules import (
    TargetRule,
    TargetRuleKind,
    compile_target_rules,
    format_target_rules,
)
from mute.ui.copy import LABEL_MATCHED_USERS, MENU_SELECT_TARGET
from mute.services.bulk_operations.group_manager.query import execute_query
from mute.services.bulk_operations.group_manager.reports import list_reports
from mute.services.bulk_operations.group_manager.snapshot import GroupSnapshot, SnapshotUser


def _workspace(tmp_path) -> Workspace:
    ws = Workspace(name="Prod", integration="pasarguard", base_url="https://panel", root=tmp_path)
    ws.ensure_dirs()
    return ws


def _snapshot() -> GroupSnapshot:
    return GroupSnapshot(
        users=(
            SnapshotUser("alice", (1, 3)),
            SnapshotUser("bob", (1,)),
            SnapshotUser("carol", (2,)),
        ),
        loaded_at=datetime(2026, 7, 28),
    )


class FakeClient:
    def __init__(self):
        self.modified: list[tuple[str, list[int]]] = []
        self.loads = 0

    def get_groups_simple(self, *, all_groups=True):
        self.loads += 1
        return [{"id": 1, "name": "a"}, {"id": 3, "name": "c"}]

    def iter_users(self, *, page_size=100):
        yield SimpleNamespace(username="alice", group_ids=[1, 3])
        yield SimpleNamespace(username="bob", group_ids=[1])

    def modify_user(self, username, *, group_ids=None):
        self.modified.append((username, list(group_ids or [])))
        return {"username": username, "group_ids": group_ids}


def test_query_include_any():
    working_set = execute_query(
        _snapshot(),
        GroupQuery(include_group_ids=(1,), match_mode=MatchMode.ANY),
    )
    assert working_set.usernames() == ("alice", "bob")


def test_query_preview_and_review():
    working_set = execute_query(
        _snapshot(),
        GroupQuery(include_group_ids=(1,), match_mode=MatchMode.ANY),
    )
    rules = (
        TargetRule(kind=TargetRuleKind.WITH_GROUPS, group_ids=(1,), require_all=False),
    )
    preview = format_query_preview(working_set, rules=rules, limit=1)
    assert "📋 Target Users" in preview
    assert LABEL_MATCHED_USERS in preview or "Matched Users" in "\n".join(preview)
    assert "(+1 more)" in preview
    review = format_review_screen(
        working_set, action_label="➕ Add Groups", group_ids=(8, 9), rules=rules
    )
    assert "🛠 Action" in review
    assert "➕ Add Groups" in review
    assert "8" in review


def test_compile_target_rules():
    rules = (
        TargetRule(kind=TargetRuleKind.ALL_USERS),
        TargetRule(kind=TargetRuleKind.WITH_GROUPS, group_ids=(1, 3), require_all=True),
        TargetRule(kind=TargetRuleKind.WITHOUT_GROUPS, group_ids=(4,)),
    )
    query = compile_target_rules(rules)
    assert query.include_group_ids == (1, 3)
    assert query.exclude_group_ids == (4,)
    assert query.match_mode is MatchMode.ALL
    text = "\n".join(format_target_rules(rules))
    assert "All Snapshot Users" in text
    assert "Users with ALL groups" in text
    assert "Users without group" in text
    assert "Include" not in text
    assert "ANY" not in text or "ANY group" in text  # "ANY group" ok in with-any label


def test_home_status_labels():
    lines = format_home_status(
        workspace="MuteVPN",
        snapshot_users=1432,
        available_groups=18,
        working_set_matched=1432,
    )
    assert any("👥 Group Manager — MuteVPN" in line for line in lines)
    assert any("Matched Users" in line for line in lines)
    assert MENU_FILTER_USERS not in lines  # menus are separate from summary
    assert MENU_SELECT_TARGET == "🎯 Select Target Users"



def test_available_groups_display():
    text = format_available_groups(GroupCatalog(groups=(GroupInfo(1), GroupInfo(3), GroupInfo(5))))
    assert "Available Groups" in text
    assert "1 3 5" in text


def test_session_and_refresh(tmp_path):
    ws = _workspace(tmp_path)
    client = FakeClient()
    service = GroupManagerApplicationService(client_factory=lambda _ws: client)
    session = service.begin_session(ws, client=client)
    service.run_query(GroupQuery(include_group_ids=(1,), match_mode=MatchMode.ANY))
    assert service.working_set() is not None
    loads_before = client.loads
    refreshed = service.refresh_snapshot(ws, client=client)
    assert refreshed.working_set is None
    assert refreshed.query is None
    assert client.loads > loads_before
    service.leave_session()
    assert service.session() is None


def test_execute_continues_on_failure(tmp_path):
    ws = _workspace(tmp_path)
    client = FakeClient()

    def boom_modify(username, *, group_ids=None):
        if username == "bob":
            raise RuntimeError("Timeout")
        client.modified.append((username, list(group_ids or [])))
        return {}

    client.modify_user = boom_modify  # type: ignore[method-assign]
    service = GroupManagerApplicationService(client_factory=lambda _ws: client)
    service.begin_session(ws, client=client)
    service.run_query(GroupQuery(include_group_ids=(1,), match_mode=MatchMode.ANY))
    report = service.execute_action(ws, "add", {"group_ids": [9]}, client=client)
    assert "mode" not in report.to_dict()
    assert report.summary.matched == 2
    assert report.summary.success == 1
    assert report.summary.failed == 1


def test_report_retention_keeps_latest_three(tmp_path):
    ws = _workspace(tmp_path)
    client = FakeClient()
    service = GroupManagerApplicationService(client_factory=lambda _ws: client)
    service.begin_session(ws, client=client)
    service.run_query(GroupQuery(include_group_ids=(1,), match_mode=MatchMode.ANY))
    for index in range(4):
        service.execute_action(ws, "add", {"group_ids": [10 + index]}, client=client)
    assert len(list_reports(ws)) == 3


def test_action_requires_working_set(tmp_path):
    ws = _workspace(tmp_path)
    client = FakeClient()
    service = GroupManagerApplicationService(client_factory=lambda _ws: client)
    service.begin_session(ws, client=client)
    with pytest.raises(GroupManagerError, match="Filter"):
        service.execute_action(ws, "add", {"group_ids": [1]}, client=client)
