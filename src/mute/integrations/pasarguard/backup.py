"""📦 Backup module.

Exports panel **users** to a single timestamped JSON backup. Current schema version
is :data:`BACKUP_VERSION` (``0.2``):

    {
        "metadata": { ... },
        "users": [ ... ]
    }

Backups are written under a year/month archive, and the most recent one is always mirrored to
``backups/backup_latest.json``:

    backups/
        backup_latest.json
        2026/
            07/
                backup_2026-07-10_18-20-00.json

Each user object is a clean operational export limited to the whitelisted :data:`FIELDS`.
Secrets and raw protocol data (proxy settings, subscription URLs, UUIDs, private keys, vmess /
vless / trojan / wireguard, etc.) are intentionally excluded — see :data:`EXCLUDED_FIELDS`.

This module is UI-agnostic: progress is reported through an optional callback so the CLI can
render it while the logic stays testable.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Callable

from ...core.constants import TOOL_NAME, VERSION
from ...core.jsonio import unique_path, write_json_atomic
from ...core.logging import get_logger
from ...core.paths import BACKUPS_DIR
from ...core.workspace import Workspace
from . import DISPLAY_NAME
from .client import PasarGuardClient

logger = get_logger("backup")

# (message, completed, total) — total 0 means "unknown/indeterminate".
ProgressHook = Callable[[str, int, int], None]

DEFAULT_BACKUP_DIR = BACKUPS_DIR
LATEST_FILENAME = "backup_latest.json"

MANIFEST_VERSION = "1"
BACKUP_VERSION = "0.2"
BACKUP_TYPE = "users"
INTEGRATION_NAME = DISPLAY_NAME

# The exact set of fields kept for each user (order preserved in output).
# Runtime/panel-only fields (admin_id, on_hold_*, next_plan) are intentionally omitted.
FIELDS: list[str] = [
    "id",
    "username",
    "status",
    "used_traffic",
    "data_limit",
    "created_at",
    "data_limit_reset_strategy",
    "note",
    "edit_at",
    "expire",
    "group_ids",
]

# Sensitive / raw fields intentionally dropped to keep the backup a clean operational export.
EXCLUDED_FIELDS: list[str] = [
    "proxy_settings",
    "subscription_url",
    "uuid",
    "private_key",
    "protocol_settings",
    "wireguard",
    "vmess",
    "vless",
    "trojan",
    "shadowsocks",
]


class BackupError(Exception):
    """Raised when a backup cannot be produced."""


@dataclass
class BackupResult:
    archive_path: Path
    latest_path: Path
    created_at: datetime
    users_count: int
    size_bytes: int
    duration_seconds: float


def _project_user(raw: dict) -> dict:
    """Reduce a raw user payload to the frozen whitelist (missing fields become null)."""
    return {field: raw.get(field) for field in FIELDS}


class BackupService:
    """Produces a JSON backup of the configured panel's users."""

    def __init__(
        self,
        client: PasarGuardClient,
        profile: Workspace,
        *,
        base_dir: Path = DEFAULT_BACKUP_DIR,
    ) -> None:
        self.client = client
        self.profile = profile
        self.base_dir = Path(base_dir)

    def run(self, progress: ProgressHook | None = None) -> BackupResult:
        started = time.perf_counter()
        created_at = datetime.now()
        logger.info("Starting export for workspace '%s'", self.profile.name)

        logger.info("Loading users...")
        users = self._load_users(progress)
        logger.info("Loaded %d users", len(users))

        payload = {
            "metadata": self._metadata(created_at, len(users)),
            "users": users,
        }

        logger.info("Writing backup...")
        archive_path = self._archive_path(created_at)
        self._write(archive_path, payload)
        latest_path = self.base_dir / LATEST_FILENAME
        self._write(latest_path, payload)

        size_bytes = archive_path.stat().st_size
        duration = time.perf_counter() - started
        logger.info(
            "Backup completed (%d users, %d bytes) → %s", len(users), size_bytes, archive_path
        )

        return BackupResult(
            archive_path=archive_path,
            latest_path=latest_path,
            created_at=created_at,
            users_count=len(users),
            size_bytes=size_bytes,
            duration_seconds=duration,
        )

    def _load_users(self, progress: ProgressHook | None) -> list[dict]:
        total = 0
        try:
            total = int(self.client.get_users(limit=1).get("total") or 0)
        except Exception:  # a missing total should not abort the export
            total = 0

        users: list[dict] = []
        if progress:
            progress("Exporting users", 0, total)
        for user in self.client.iter_users():
            users.append(_project_user(user.raw))
            if progress:
                progress("Exporting users", len(users), total)
        return users

    def _metadata(self, created_at: datetime, users_count: int) -> dict:
        return {
            "manifest_version": MANIFEST_VERSION,
            "backup_version": BACKUP_VERSION,
            "backup_type": BACKUP_TYPE,
            "tool": TOOL_NAME,
            "integration": INTEGRATION_NAME,
            "tool_version": VERSION,
            "panel_profile": self.profile.name,
            "panel_key": self.profile.username or self.profile.name,
            "panel_url": self.profile.base_url,
            "created_at": created_at.isoformat(timespec="seconds"),
            "users_count": users_count,
            "fields": FIELDS,
            "excluded_fields": EXCLUDED_FIELDS,
        }

    def _archive_path(self, created_at: datetime) -> Path:
        directory = self.base_dir / created_at.strftime("%Y") / created_at.strftime("%m")
        directory.mkdir(parents=True, exist_ok=True)
        stem = f"backup_{created_at.strftime('%Y-%m-%d_%H-%M-%S')}"
        return unique_path(directory, stem, ".json")

    @staticmethod
    def _write(path: Path, payload: dict) -> None:
        try:
            write_json_atomic(path, payload, ensure_ascii=False)
        except OSError as exc:
            raise BackupError(f"Could not write backup to {path}: {exc}") from exc


@dataclass
class LatestBackup:
    """Status of the most recent backup, read from ``backup_latest.json`` only."""

    created_at: datetime
    users: int
    size_bytes: int


def latest_backup(base_dir: Path = DEFAULT_BACKUP_DIR) -> LatestBackup | None:
    """Read ``backup_latest.json`` and return its status, or ``None`` if unavailable.

    Only this single file is consulted — the archive folder is never scanned.
    """
    latest = Path(base_dir) / LATEST_FILENAME
    if not latest.exists():
        return None
    try:
        meta = json.loads(latest.read_text(encoding="utf-8")).get("metadata", {})
        created = datetime.fromisoformat(meta["created_at"])
    except (json.JSONDecodeError, OSError, KeyError, ValueError):
        return None

    try:
        size_bytes = latest.stat().st_size
    except OSError:
        size_bytes = 0
    return LatestBackup(
        created_at=created,
        users=int(meta.get("users_count") or 0),
        size_bytes=size_bytes,
    )
