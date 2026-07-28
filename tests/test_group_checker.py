"""Unit tests for the Group Checker engine, reader, queries, and application service."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

import pytest

from mute.core.logging import get_logger, use_workspace
from mute.core.workspace import Workspace
from mute.services.group_checker import (
    GroupCheckerApplicationService,
    GroupCheckerOperationError,
    GroupQueryDescriptor,
    GroupQueryType,
    format_group_ids,
    parse_group_ids,
)
from mute.services.group_checker.engine import GroupCheckerService
from mute.services.group_checker.models import BackupSource
from mute.services.group_checker.queries import QUERY_REGISTRY, RequiredGroupsQuery, build_query
from mute.services.group_checker.reader import BackupReadError, BackupReader, BackupUser


def _workspace(tmp_path: Path) -> Workspace:
    ws = Workspace(name="Prod", integration="pasarguard", base_url="https://panel", root=tmp_path)
    ws.ensure_dirs()
    use_workspace(ws.logs_dir)
    return ws


def _write_backup(ws: Workspace, name: str, users: list[dict], *, created: str = "2026-07-15T12:00:00") -> Path:
    directory = ws.backups_dir / "2026" / "07"
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / name
    payload = {
        "metadata": {
            "created_at": created,
            "users_count": len(users),
            "backup_type": "users",
        },
        "users": users,
    }
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


# -- parse / format helpers -----------------------------------------------------------


def test_parse_group_ids_accepts_comma_and_space():
    assert parse_group_ids("1, 3") == (1, 3)
    assert parse_group_ids("1 3 5") == (1, 3, 5)
    assert parse_group_ids("  7,8,  9 ") == (7, 8, 9)


def test_parse_group_ids_deduplicates_preserving_order():
    assert parse_group_ids("1, 3, 1, 3") == (1, 3)


def test_parse_group_ids_rejects_empty_and_invalid():
    with pytest.raises(ValueError):
        parse_group_ids("")
    with pytest.raises(ValueError):
        parse_group_ids("1, abc")


def test_format_group_ids():
    assert format_group_ids((1, 3)) == "1, 3"
    assert format_group_ids(()) == "—"


# -- BackupReader ---------------------------------------------------------------------


def test_reader_loads_valid_backup(tmp_path):
    ws = _workspace(tmp_path)
    path = _write_backup(
        ws,
        "backup_2026-07-15_12-00-00.json",
        [
            {"username": "alice", "group_ids": [1, 3], "status": "active"},
            {"username": "bob", "group_ids": [1]},
            {"username": "carol", "group_ids": None},
        ],
    )
    snapshot = BackupReader().load(path)
    assert snapshot.archive_name == path.name
    assert snapshot.users_count == 3
    assert snapshot.users[0] == BackupUser("alice", (1, 3))
    assert snapshot.users[1] == BackupUser("bob", (1,))
    assert snapshot.users[2] == BackupUser("carol", ())


def test_reader_skips_malformed_users(tmp_path):
    ws = _workspace(tmp_path)
    path = _write_backup(
        ws,
        "backup_bad_users.json",
        [
            "not-an-object",
            {"username": "", "group_ids": [1]},
            {"group_ids": [1]},
            {"username": "ok", "group_ids": [1, "x", 2]},
        ],
    )
    snapshot = BackupReader().load(path)
    assert len(snapshot.users) == 1
    assert snapshot.users[0].username == "ok"
    assert snapshot.users[0].group_ids == (1, 2)


def test_reader_empty_users_list(tmp_path):
    ws = _workspace(tmp_path)
    path = _write_backup(ws, "backup_empty.json", [])
    snapshot = BackupReader().load(path)
    assert snapshot.users == ()
    assert snapshot.users_count == 0


def test_reader_rejects_missing_file(tmp_path):
    with pytest.raises(BackupReadError):
        BackupReader().load(tmp_path / "missing.json")


def test_reader_rejects_invalid_json(tmp_path):
    path = tmp_path / "broken.json"
    path.write_text("{not json", encoding="utf-8")
    with pytest.raises(BackupReadError):
        BackupReader().load(path)


def test_reader_rejects_missing_top_level_keys(tmp_path):
    path = tmp_path / "partial.json"
    path.write_text(json.dumps({"users": []}), encoding="utf-8")
    with pytest.raises(BackupReadError):
        BackupReader().load(path)


def test_reader_rejects_non_list_users(tmp_path):
    path = tmp_path / "bad.json"
    path.write_text(json.dumps({"metadata": {}, "users": {}}), encoding="utf-8")
    with pytest.raises(BackupReadError):
        BackupReader().load(path)


# -- RequiredGroupsQuery + registry ---------------------------------------------------


def test_required_groups_evaluate_missing_any():
    query = RequiredGroupsQuery((1, 3))
    assert query.evaluate(BackupUser("a", (1, 3))) is False  # has all — not in result
    assert query.evaluate(BackupUser("b", (1,))) is True  # missing 3
    assert query.evaluate(BackupUser("c", (3,))) is True  # missing 1
    assert query.evaluate(BackupUser("d", ())) is True  # missing both
    assert query.evaluate(BackupUser("e", (1, 2, 3))) is False


def test_required_groups_missing_for():
    query = RequiredGroupsQuery((1, 3))
    assert query.missing_for(BackupUser("b", (1,))) == (3,)
    assert query.missing_for(BackupUser("a", (1, 3))) == ()


def test_query_registry_contains_only_required_groups():
    assert set(QUERY_REGISTRY) == {GroupQueryType.REQUIRED_GROUPS}
    built = build_query(GroupQueryType.REQUIRED_GROUPS, (1, 3))
    assert built.label == "Required Groups"
    assert built.group_ids == (1, 3)


def test_build_query_unknown_type_raises(monkeypatch):
    from mute.services.group_checker import queries

    monkeypatch.setattr(queries, "QUERY_REGISTRY", {})
    with pytest.raises(ValueError):
        build_query(GroupQueryType.REQUIRED_GROUPS, (1,))


# -- GroupCheckerService (engine) -----------------------------------------------------


def test_engine_returns_users_missing_required_groups(tmp_path):
    ws = _workspace(tmp_path)
    path = _write_backup(
        ws,
        "backup_engine.json",
        [
            {"username": "alice", "group_ids": [1, 3]},
            {"username": "bob", "group_ids": [1]},
            {"username": "carol", "group_ids": []},
        ],
    )
    result = GroupCheckerService().run(path, RequiredGroupsQuery((1, 3)))
    assert result.matching_users == 2
    assert result.total_users == 3
    names = [row.username for row in result.users]
    assert names == ["bob", "carol"]
    bob = result.users[0]
    assert bob.current_group_ids == (1,)
    assert bob.missing_group_ids == (3,)
    carol = result.users[1]
    assert carol.current_group_ids == ()
    assert carol.missing_group_ids == (1, 3)


def test_engine_all_users_match_when_none_have_required(tmp_path):
    ws = _workspace(tmp_path)
    path = _write_backup(ws, "backup_all.json", [{"username": "x", "group_ids": [9]}])
    result = GroupCheckerService().run(path, RequiredGroupsQuery((1,)))
    assert result.matching_users == 1


def test_engine_no_matches_when_all_have_required(tmp_path):
    ws = _workspace(tmp_path)
    path = _write_backup(ws, "backup_ok.json", [{"username": "x", "group_ids": [1, 3]}])
    result = GroupCheckerService().run(path, RequiredGroupsQuery((1, 3)))
    assert result.matching_users == 0
    assert result.users == ()


# -- Application service --------------------------------------------------------------


def test_application_list_backups(tmp_path):
    ws = _workspace(tmp_path)
    _write_backup(ws, "backup_2026-07-15_12-00-00.json", [{"username": "a", "group_ids": [1]}])
    sources = GroupCheckerApplicationService().list_backups(ws)
    assert len(sources) == 1
    assert isinstance(sources[0], BackupSource)
    assert sources[0].name.startswith("backup_")
    assert sources[0].users == 1


def test_application_run_query_returns_dto_and_history(tmp_path):
    ws = _workspace(tmp_path)
    _write_backup(
        ws,
        "backup_2026-07-15_12-00-00.json",
        [
            {"username": "alice", "group_ids": [1, 3]},
            {"username": "bob", "group_ids": [1]},
        ],
    )
    service = GroupCheckerApplicationService()
    result = service.run_query(
        ws,
        "backup_2026-07-15_12-00-00.json",
        GroupQueryDescriptor(GroupQueryType.REQUIRED_GROUPS, (1, 3)),
    )
    assert result.workspace == "Prod"
    assert result.query_type == "required_groups"
    assert result.query_label == "Required Groups"
    assert result.matching_users == 1
    assert result.users[0].username == "bob"
    assert result.required_group_ids == (1, 3)

    history_files = list(ws.history_dir.glob("*_group_checker.json"))
    assert len(history_files) == 1
    payload = json.loads(history_files[0].read_text(encoding="utf-8"))
    assert payload["type"] == "group_checker"
    assert payload["status"] == "success"
    assert payload["matching_users"] == 1
    assert payload["required_groups"] == [1, 3]
    assert payload["matching_usernames"] == ["bob"]
    keys = list(payload.keys())
    assert keys.index("matching_usernames") == keys.index("matching_users") + 1
    assert keys.index("duration") == keys.index("matching_usernames") + 1


def test_application_history_empty_matching_usernames(tmp_path):
    ws = _workspace(tmp_path)
    _write_backup(
        ws,
        "backup_2026-07-15_12-00-00.json",
        [{"username": "alice", "group_ids": [1, 3]}],
    )
    GroupCheckerApplicationService().run_query(
        ws,
        "backup_2026-07-15_12-00-00.json",
        GroupQueryDescriptor(GroupQueryType.REQUIRED_GROUPS, (1, 3)),
    )
    history_files = list(ws.history_dir.glob("*_group_checker.json"))
    payload = json.loads(history_files[0].read_text(encoding="utf-8"))
    assert payload["matching_users"] == 0
    assert payload["matching_usernames"] == []


def test_application_history_preserves_username_order(tmp_path):
    ws = _workspace(tmp_path)
    _write_backup(
        ws,
        "backup_2026-07-15_12-00-00.json",
        [
            {"username": "carol", "group_ids": []},
            {"username": "alice", "group_ids": [1]},
            {"username": "bob", "group_ids": [1, 3]},
        ],
    )
    GroupCheckerApplicationService().run_query(
        ws,
        "backup_2026-07-15_12-00-00.json",
        GroupQueryDescriptor(GroupQueryType.REQUIRED_GROUPS, (1, 3)),
    )
    payload = json.loads(next(ws.history_dir.glob("*_group_checker.json")).read_text(encoding="utf-8"))
    assert payload["matching_usernames"] == ["carol", "alice"]


def test_application_run_query_writes_log(tmp_path):
    ws = _workspace(tmp_path)
    _write_backup(ws, "backup_2026-07-15_12-00-00.json", [{"username": "a", "group_ids": []}])
    GroupCheckerApplicationService().run_query(
        ws,
        "backup_2026-07-15_12-00-00.json",
        GroupQueryDescriptor(GroupQueryType.REQUIRED_GROUPS, (1,)),
    )
    log = (ws.logs_dir / "group_checker.log").read_text(encoding="utf-8")
    assert "Running Required Groups" in log
    assert "Query completed" in log


def test_application_rejects_empty_group_ids(tmp_path):
    ws = _workspace(tmp_path)
    _write_backup(ws, "backup_2026-07-15_12-00-00.json", [])
    with pytest.raises(GroupCheckerOperationError):
        GroupCheckerApplicationService().run_query(
            ws,
            "backup_2026-07-15_12-00-00.json",
            GroupQueryDescriptor(GroupQueryType.REQUIRED_GROUPS, ()),
        )


def test_application_rejects_missing_backup(tmp_path):
    ws = _workspace(tmp_path)
    with pytest.raises(GroupCheckerOperationError, match="not found"):
        GroupCheckerApplicationService().run_query(
            ws,
            "backup_missing.json",
            GroupQueryDescriptor(GroupQueryType.REQUIRED_GROUPS, (1,)),
        )


def test_reader_rejects_non_object_payload(tmp_path):
    path = tmp_path / "list.json"
    path.write_text("[]", encoding="utf-8")
    with pytest.raises(BackupReadError):
        BackupReader().load(path)


def test_reader_non_list_group_ids_become_empty(tmp_path):
    ws = _workspace(tmp_path)
    path = _write_backup(ws, "backup_gid.json", [{"username": "a", "group_ids": "oops"}])
    snapshot = BackupReader().load(path)
    assert snapshot.users[0].group_ids == ()


def test_reader_created_at_falls_back_to_mtime(tmp_path):
    ws = _workspace(tmp_path)
    path = _write_backup(ws, "backup_mtime.json", [{"username": "a", "group_ids": []}])
    # Corrupt created_at so isoformat fails.
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["metadata"]["created_at"] = "not-a-date"
    path.write_text(json.dumps(payload), encoding="utf-8")
    snapshot = BackupReader().load(path)
    assert isinstance(snapshot.created_at, datetime)


def test_reader_users_count_fallback(tmp_path):
    ws = _workspace(tmp_path)
    path = _write_backup(ws, "backup_count.json", [{"username": "a", "group_ids": [1]}])
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["metadata"]["users_count"] = "nope"
    path.write_text(json.dumps(payload), encoding="utf-8")
    snapshot = BackupReader().load(path)
    assert snapshot.users_count == 1


def test_application_history_failure_is_non_fatal(tmp_path, monkeypatch):
    ws = _workspace(tmp_path)
    _write_backup(ws, "backup_2026-07-15_12-00-00.json", [{"username": "a", "group_ids": []}])

    def boom(*a, **k):
        raise OSError("disk full")

    monkeypatch.setattr("mute.services.group_checker.service.record_job", boom)
    result = GroupCheckerApplicationService().run_query(
        ws,
        "backup_2026-07-15_12-00-00.json",
        GroupQueryDescriptor(GroupQueryType.REQUIRED_GROUPS, (1,)),
    )
    assert result.matching_users == 1


def test_application_users_from_corrupt_archive_metadata(tmp_path):
    ws = _workspace(tmp_path)
    directory = ws.backups_dir / "2026" / "07"
    directory.mkdir(parents=True)
    path = directory / "backup_2026-07-15_12-00-00.json"
    path.write_text("{}", encoding="utf-8")  # valid JSON but no metadata users_count usable via archives path
    # archives() will still list it; users count falls back to 0
    sources = GroupCheckerApplicationService().list_backups(ws)
    assert sources[0].users == 0


def test_application_wraps_unknown_query_type(tmp_path, monkeypatch):
    ws = _workspace(tmp_path)
    _write_backup(ws, "backup_2026-07-15_12-00-00.json", [{"username": "a", "group_ids": []}])
    from mute.services.group_checker import queries

    monkeypatch.setattr(queries, "QUERY_REGISTRY", {})
    with pytest.raises(GroupCheckerOperationError):
        GroupCheckerApplicationService().run_query(
            ws,
            "backup_2026-07-15_12-00-00.json",
            GroupQueryDescriptor(GroupQueryType.REQUIRED_GROUPS, (1,)),
        )


def test_application_users_from_unreadable_archive(tmp_path):
    ws = _workspace(tmp_path)
    directory = ws.backups_dir / "2026" / "07"
    directory.mkdir(parents=True)
    path = directory / "backup_2026-07-15_12-00-00.json"
    path.write_text("{broken", encoding="utf-8")
    sources = GroupCheckerApplicationService().list_backups(ws)
    assert sources[0].users == 0


def test_application_wraps_corrupt_backup(tmp_path):
    ws = _workspace(tmp_path)
    directory = ws.backups_dir / "2026" / "07"
    directory.mkdir(parents=True)
    path = directory / "backup_2026-07-15_12-00-00.json"
    path.write_text("{broken", encoding="utf-8")
    with pytest.raises(GroupCheckerOperationError):
        GroupCheckerApplicationService().run_query(
            ws,
            path.name,
            GroupQueryDescriptor(GroupQueryType.REQUIRED_GROUPS, (1,)),
        )


# CLI Group Manager no longer uses the backup Required Groups confirmation flow.
# See tests/test_group_manager.py and tests/test_group_checker_cli.py.
