import json

from mute.core.profiles import Profile
from mute.integrations.pasarguard.backup import (
    EXCLUDED_FIELDS,
    FIELDS,
    BackupService,
    latest_backup,
)
from mute.integrations.pasarguard.models import User


class FakeClient:
    """Stand-in for PasarGuardClient that serves users from memory."""

    def __init__(self, users):
        self._users = users

    def get_users(self, *, offset=0, limit=100):
        return {"users": self._users[offset : offset + limit], "total": len(self._users)}

    def iter_users(self, *, page_size=100):
        for entry in self._users:
            yield User.from_dict(entry)


def _raw_user(i):
    # A realistic raw payload including secrets that must be excluded.
    return {
        "id": i,
        "username": f"user{i}",
        "status": "active",
        "used_traffic": 100,
        "data_limit": 1000,
        "created_at": "2026-05-30T09:36:58Z",
        "edit_at": "2026-07-07T09:01:00Z",
        "expire": "2026-08-07T20:59:59Z",
        "group_ids": [1, 3],
        "note": "n",
        "data_limit_reset_strategy": "no_reset",
        # Runtime/panel-only fields — must not appear in the exported backup.
        "admin_id": None,
        "on_hold_timeout": None,
        "on_hold_expire_duration": None,
        "next_plan": None,
        "proxy_settings": {"vmess": {"id": "secret"}, "wireguard": {"private_key": "x"}},
        "subscription_url": "https://secret",
        "admin": {"username": "boss"},
        "lifetime_used_traffic": 999,
    }


def _users(n):
    return [_raw_user(i) for i in range(n)]


def _profile():
    return Profile(name="prod", base_url="https://panel", username="boss", password="pw")


def test_backup_writes_archive_and_latest(tmp_path):
    result = BackupService(FakeClient(_users(3)), _profile(), base_dir=tmp_path).run()

    assert result.archive_path.exists()
    assert result.latest_path == tmp_path / "backup_latest.json"
    assert result.latest_path.exists()
    assert result.users_count == 3
    assert result.size_bytes > 0
    assert result.duration_seconds >= 0


def test_archive_uses_year_month_structure(tmp_path):
    result = BackupService(FakeClient(_users(1)), _profile(), base_dir=tmp_path).run()
    created = result.created_at
    expected_dir = tmp_path / created.strftime("%Y") / created.strftime("%m")
    assert result.archive_path.parent == expected_dir
    assert result.archive_path.name.startswith("backup_")


def test_frozen_top_level_shape(tmp_path):
    result = BackupService(FakeClient(_users(2)), _profile(), base_dir=tmp_path).run()
    payload = json.loads(result.latest_path.read_text(encoding="utf-8"))
    assert set(payload.keys()) == {"metadata", "users"}
    assert len(payload["users"]) == 2


def test_metadata_contents(tmp_path):
    result = BackupService(FakeClient(_users(2)), _profile(), base_dir=tmp_path).run()
    meta = json.loads(result.latest_path.read_text(encoding="utf-8"))["metadata"]

    expected_keys = {
        "manifest_version",
        "backup_version",
        "backup_type",
        "tool",
        "integration",
        "tool_version",
        "panel_profile",
        "panel_key",
        "panel_url",
        "created_at",
        "users_count",
        "fields",
        "excluded_fields",
    }
    assert set(meta.keys()) == expected_keys
    assert meta["backup_type"] == "users"
    assert meta["tool"] == "Mute"
    assert meta["integration"] == "PasarGuard"
    assert meta["manifest_version"] == "1"
    assert meta["backup_version"] == "0.2"
    assert meta["panel_profile"] == "prod"
    assert meta["users_count"] == 2
    assert meta["fields"] == FIELDS
    assert meta["excluded_fields"] == EXCLUDED_FIELDS


def test_latest_backup_reads_only_latest_file(tmp_path):
    assert latest_backup(tmp_path) is None  # nothing yet

    BackupService(FakeClient(_users(5)), _profile(), base_dir=tmp_path).run()
    status = latest_backup(tmp_path)

    assert status is not None
    assert status.users == 5
    assert status.size_bytes > 0


def test_user_object_is_whitelisted_and_ordered(tmp_path):
    result = BackupService(FakeClient(_users(1)), _profile(), base_dir=tmp_path).run()
    user = json.loads(result.latest_path.read_text(encoding="utf-8"))["users"][0]

    assert list(user.keys()) == FIELDS  # exact set and order
    for secret in ("proxy_settings", "subscription_url", "admin", "lifetime_used_traffic"):
        assert secret not in user
    for runtime in ("admin_id", "on_hold_timeout", "on_hold_expire_duration", "next_plan"):
        assert runtime not in user



def test_progress_hook_final_count(tmp_path):
    calls = []
    BackupService(FakeClient(_users(2)), _profile(), base_dir=tmp_path).run(
        progress=lambda msg, done, total: calls.append((msg, done, total))
    )
    assert calls
    assert calls[-1][1] == 2


def test_archive_listing_excludes_latest_mirror(tmp_path):
    from mute.core.workspace import Workspace
    from mute.services.backup import BackupApplicationService

    ws = Workspace(name="P", integration="pasarguard", base_url="https://x", root=tmp_path)
    ws.ensure_dirs()
    archive = ws.backups_dir / "2026" / "07" / "backup_2026-07-10_12-00-00.json"
    archive.parent.mkdir(parents=True)
    archive.write_text("{}", encoding="utf-8")
    (ws.backups_dir / "backup_latest.json").write_text("{}", encoding="utf-8")

    archives = BackupApplicationService().archives(ws)
    assert len(archives) == 1
    assert archives[0].path.name.startswith("backup_2026")
