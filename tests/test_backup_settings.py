"""Tests for per-workspace Auto Backup settings and Max Backups retention."""

from __future__ import annotations

from datetime import datetime, timedelta
from unittest.mock import MagicMock

from mute.core.workspace import DEFAULT_MAX_BACKUPS, Workspace, WorkspaceStore
from mute.services.backup import (
    BackupApplicationService,
    format_auto_backup_lines,
    format_max_backups_lines,
    parse_auto_backup_interval,
    parse_max_backups,
)
from mute.services.workspace import WorkspaceApplicationService
from mute.ui.copy import STATUS_AUTO_DISABLED, STATUS_AUTO_ENABLED


def _store(tmp_path):
    return WorkspaceStore(root=tmp_path / "workspaces", registry_path=tmp_path / "config" / "workspaces.json")


def _workspace(tmp_path, name="Prod", **kwargs) -> Workspace:
    store = _store(tmp_path)
    ws = Workspace(name=name, integration="pasarguard", base_url="https://panel", **kwargs)
    store.create(ws, make_active=True)
    return store.get(name)


def test_workspace_backup_settings_persist(tmp_path):
    store = _store(tmp_path)
    ws = Workspace(name="A", integration="pasarguard", base_url="https://a")
    store.create(ws, make_active=True)
    assert ws.max_backups == DEFAULT_MAX_BACKUPS
    assert ws.auto_backup_enabled is False

    service = WorkspaceApplicationService(store)
    service.save_backup_settings(ws, auto_backup_enabled=True, auto_backup_interval=30, max_backups=20)

    reloaded = store.get("A")
    assert reloaded is not None
    assert reloaded.auto_backup_enabled is True
    assert reloaded.auto_backup_interval == 30
    assert reloaded.max_backups == 20
    manifest = reloaded.to_dict()
    assert manifest["auto_backup_enabled"] is True
    assert manifest["auto_backup_interval"] == 30
    assert manifest["max_backups"] == 20


def test_legacy_manifest_gets_backup_defaults(tmp_path):
    ws = Workspace.from_dict(
        {"workspace_name": "Legacy", "integration": "pasarguard", "base_url": "https://x"}
    )
    assert ws.auto_backup_enabled is False
    assert ws.auto_backup_interval == 0
    assert ws.max_backups == DEFAULT_MAX_BACKUPS


def test_workspace_isolation_of_backup_settings(tmp_path):
    store = _store(tmp_path)
    a = store.create(Workspace(name="A", integration="pasarguard", base_url="https://a"))
    b = store.create(Workspace(name="B", integration="pasarguard", base_url="https://b"))
    service = WorkspaceApplicationService(store)
    service.save_backup_settings(a, auto_backup_enabled=True, auto_backup_interval=5, max_backups=20)
    service.save_backup_settings(b, auto_backup_enabled=False, max_backups=5)

    a2, b2 = store.get("A"), store.get("B")
    assert a2.auto_backup_enabled is True and a2.auto_backup_interval == 5 and a2.max_backups == 20
    assert b2.auto_backup_enabled is False and b2.max_backups == 5


def test_parse_interval_and_max_backups():
    assert parse_auto_backup_interval("30") == 30
    assert parse_auto_backup_interval("1") == 1
    assert parse_auto_backup_interval("4320") == 4320
    for bad in ("0", "4321", "abc", ""):
        try:
            parse_auto_backup_interval(bad)
            assert False, bad
        except ValueError:
            pass

    assert parse_max_backups("10") == 10
    assert parse_max_backups("1") == 1
    assert parse_max_backups("100") == 100
    for bad in ("0", "101", "x"):
        try:
            parse_max_backups(bad)
            assert False, bad
        except ValueError:
            pass


def test_enforce_retention_keeps_newest(tmp_path):
    ws = _workspace(tmp_path, max_backups=2)
    service = BackupApplicationService()
    base = datetime(2026, 7, 28, 12, 0, 0)
    paths = []
    for index in range(4):
        created = base + timedelta(minutes=index)
        directory = ws.backups_dir / created.strftime("%Y") / created.strftime("%m")
        directory.mkdir(parents=True, exist_ok=True)
        path = directory / f"backup_{created.strftime('%Y-%m-%d_%H-%M-%S')}.json"
        path.write_text(
            '{"metadata":{"created_at":"%s","users_count":1},"users":[]}'
            % created.isoformat(timespec="seconds"),
            encoding="utf-8",
        )
        paths.append(path)

    deleted = service.enforce_retention(ws)
    assert deleted == 2
    remaining = {archive.path.name for archive in service.archives(ws)}
    assert remaining == {paths[2].name, paths[3].name}


def test_is_auto_backup_due(tmp_path):
    ws = _workspace(tmp_path, auto_backup_enabled=True, auto_backup_interval=30)
    service = BackupApplicationService()
    assert service.is_auto_backup_due(ws) is True  # no latest → due

    created = datetime.now() - timedelta(minutes=10)
    directory = ws.backups_dir / created.strftime("%Y") / created.strftime("%m")
    directory.mkdir(parents=True, exist_ok=True)
    archive = directory / f"backup_{created.strftime('%Y-%m-%d_%H-%M-%S')}.json"
    archive.write_text(
        '{"metadata":{"created_at":"%s","users_count":1},"users":[]}'
        % created.isoformat(timespec="seconds"),
        encoding="utf-8",
    )
    (ws.backups_dir / "backup_latest.json").write_text(archive.read_text(encoding="utf-8"), encoding="utf-8")

    assert service.is_auto_backup_due(ws) is False
    assert service.is_auto_backup_due(ws, now=datetime.now() + timedelta(minutes=25)) is True

    ws.auto_backup_enabled = False
    assert service.is_auto_backup_due(ws) is False


def test_format_auto_and_max_lines(tmp_path):
    disabled = _workspace(tmp_path, name="Off")
    lines = format_auto_backup_lines(disabled)
    assert STATUS_AUTO_DISABLED in lines
    assert "—" in lines

    enabled = _workspace(
        tmp_path, name="On", auto_backup_enabled=True, auto_backup_interval=30, max_backups=7
    )
    lines = format_auto_backup_lines(enabled)
    assert STATUS_AUTO_ENABLED in lines
    assert "30 minutes" in lines
    assert "7" in format_max_backups_lines(enabled)


def test_create_export_runs_retention(tmp_path, monkeypatch):
    ws = _workspace(tmp_path, max_backups=1)
    service = BackupApplicationService()
    called = {"retention": False}

    def fake_run(progress=None):
        created = datetime(2026, 7, 28, 15, 0, 0)
        directory = ws.backups_dir / "2026" / "07"
        directory.mkdir(parents=True, exist_ok=True)
        path = directory / "backup_2026-07-28_15-00-00.json"
        path.write_text(
            '{"metadata":{"created_at":"2026-07-28T15:00:00","users_count":1},"users":[]}',
            encoding="utf-8",
        )
        # older archive that retention should remove
        older = directory / "backup_2026-07-28_14-00-00.json"
        older.write_text(
            '{"metadata":{"created_at":"2026-07-28T14:00:00","users_count":1},"users":[]}',
            encoding="utf-8",
        )
        return MagicMock(
            users_count=1,
            size_bytes=10,
            duration_seconds=0.1,
            created_at=created,
            archive_path=path,
        )

    monkeypatch.setattr(
        "mute.services.backup.service.BackupService",
        lambda *args, **kwargs: MagicMock(run=fake_run),
    )
    monkeypatch.setattr(
        "mute.services.backup.service.create_client",
        lambda workspace: MagicMock(),
    )
    monkeypatch.setattr("mute.services.backup.service.record_job", lambda *a, **k: None)

    summary = service.create_export(ws)
    assert summary.archive_name == "backup_2026-07-28_15-00-00.json"
    names = [a.path.name for a in service.archives(ws)]
    assert names == ["backup_2026-07-28_15-00-00.json"]
