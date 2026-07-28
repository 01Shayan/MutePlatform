"""Backup operations independent of any user interface."""

from __future__ import annotations

import json
import shutil
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from ...core.integrations import integration_name
from ...core.history import record_job
from ...core.logging import get_logger
from ...core.timefmt import relative_time
from ...core.workspace import DEFAULT_MAX_BACKUPS, Workspace
from ...integrations.pasarguard.backup import LATEST_FILENAME, BackupService, LatestBackup, latest_backup
from ...integrations.pasarguard.client import PasarGuardError, create_client


class BackupOperationError(Exception):
    """A safe, interface-ready explanation of a backup operation failure."""


logger = get_logger("backup")

MIN_AUTO_BACKUP_INTERVAL = 1
MAX_AUTO_BACKUP_INTERVAL = 4320  # 3 days
MIN_MAX_BACKUPS = 1
MAX_MAX_BACKUPS = 100


@dataclass(frozen=True)
class BackupSummary:
    workspace: str
    users: int
    size_bytes: int
    duration_seconds: float
    created_at: datetime
    archive_name: str
    integration: str

    @property
    def history(self) -> dict:
        return {
            "type": "backup", "status": "success", "workspace": self.workspace,
            "integration": self.integration, "users": self.users,
            "duration": round(self.duration_seconds, 1),
        }


@dataclass(frozen=True)
class BackupArchive:
    path: Path
    created_at: datetime
    size_bytes: int
    users: int | None = None


@dataclass(frozen=True)
class BackupDownload:
    filename: str
    content: bytes


class BackupApplicationService:
    """Coordinates export, archive inspection, retention, and archive deletion."""

    def prepare_export(self, workspace: Workspace) -> list[tuple[str, str]]:
        client = create_client(workspace)
        try:
            admin = client.test_connection()
            users = int(client.get_users(limit=1).get("total") or 0)
        except PasarGuardError as exc:
            raise BackupOperationError(f"Could not connect to the panel.\n{exc}") from exc
        admin_name = str(admin["username"]) if isinstance(admin, dict) and admin.get("username") else "—"
        return [
            ("Workspace", workspace.name), ("Panel", integration_name(workspace.integration)),
            ("URL", workspace.base_url), ("Admin", admin_name),
            ("Estimated Users", str(users)), ("Destination", "workspace/backups/"),
        ]

    def create_export(self, workspace: Workspace, progress=None) -> BackupSummary:
        """Create a backup, then enforce Max Backups retention for this workspace.

        Manual and Auto Backup both call this single pipeline entry point.
        """
        try:
            result = BackupService(create_client(workspace), workspace, base_dir=workspace.backups_dir).run(progress)
        except PasarGuardError as exc:
            raise BackupOperationError(str(exc)) from exc
        summary = BackupSummary(
            workspace=workspace.name, users=result.users_count, size_bytes=result.size_bytes,
            duration_seconds=result.duration_seconds, created_at=result.created_at,
            archive_name=result.archive_path.name, integration=integration_name(workspace.integration),
        )
        try:
            record_job(summary.history, jobs_dir=workspace.history_dir)
        except OSError as exc:  # History is best-effort and must not fail an export.
            logger.warning("Could not record job history: %s", exc)
        self.enforce_retention(workspace)
        return summary

    def enforce_retention(self, workspace: Workspace) -> int:
        """Keep only the newest ``max_backups`` archives in this workspace. Returns deleted count."""
        limit = _clamp_max_backups(workspace.max_backups)
        archives = self.archives(workspace)  # newest first
        deleted = 0
        for archive in archives[limit:]:
            try:
                archive.path.unlink(missing_ok=True)
                deleted += 1
            except OSError as exc:
                logger.warning("Could not delete old backup '%s': %s", archive.path, exc)
        if deleted:
            self._resync_latest(workspace)
            logger.info(
                "Backup retention for '%s': kept %d, deleted %d",
                workspace.name,
                limit,
                deleted,
            )
        return deleted

    def is_auto_backup_due(self, workspace: Workspace, *, now: datetime | None = None) -> bool:
        """True when Auto Backup is enabled and the interval has elapsed since the latest backup."""
        if not workspace.auto_backup_enabled:
            return False
        interval = int(workspace.auto_backup_interval or 0)
        if interval < MIN_AUTO_BACKUP_INTERVAL:
            return False
        latest = self.latest(workspace)
        if latest is None:
            return True
        current = now or datetime.now()
        age_minutes = (current - latest.created_at).total_seconds() / 60.0
        return age_minutes >= interval

    def due_auto_backup_workspaces(self, workspaces: list[Workspace]) -> list[Workspace]:
        return [workspace for workspace in workspaces if self.is_auto_backup_due(workspace)]

    def latest(self, workspace: Workspace) -> LatestBackup | None:
        return latest_backup(workspace.backups_dir)

    def archives(self, workspace: Workspace) -> list[BackupArchive]:
        directory = workspace.backups_dir
        if not directory.exists():
            return []
        paths = sorted(
            (path for path in directory.rglob("backup_*.json") if path.name != LATEST_FILENAME),
            key=lambda path: path.name, reverse=True,
        )
        return [BackupApplicationService._to_archive(path) for path in paths]

    def delete_archive(self, workspace: Workspace, archive: BackupArchive) -> None:
        archive.path.unlink(missing_ok=True)
        self._resync_latest(workspace)

    def delete_all_archives(self, workspace: Workspace) -> None:
        for archive in self.archives(workspace):
            archive.path.unlink(missing_ok=True)
        (workspace.backups_dir / LATEST_FILENAME).unlink(missing_ok=True)

    def download_archive(self, workspace: Workspace, archive_name: str) -> BackupDownload | None:
        """Return an existing archive for an interface to upload; never creates a backup."""
        archive = next((item for item in self.archives(workspace) if item.path.name == archive_name), None)
        if archive is None:
            return None
        try:
            return BackupDownload(archive.path.name, archive.path.read_bytes())
        except OSError as exc:
            raise BackupOperationError(f"Could not read backup archive.\n{exc}") from exc

    def _resync_latest(self, workspace: Workspace) -> None:
        latest_path = workspace.backups_dir / LATEST_FILENAME
        archives = self.archives(workspace)
        if archives:
            shutil.copyfile(archives[0].path, latest_path)
        elif latest_path.exists():
            latest_path.unlink()

    @staticmethod
    def _to_archive(path: Path) -> BackupArchive:
        created_at, users = BackupApplicationService._read_metadata(path)
        return BackupArchive(path, created_at, path.stat().st_size, users)

    @staticmethod
    def _read_metadata(path: Path) -> tuple[datetime, int | None]:
        try:
            metadata = json.loads(path.read_text(encoding="utf-8")).get("metadata", {})
            created_at = datetime.fromisoformat(metadata["created_at"])
            raw_users = metadata.get("users_count")
            users = int(raw_users) if raw_users is not None else None
            return created_at, users
        except (json.JSONDecodeError, OSError, KeyError, TypeError, ValueError):
            return datetime.fromtimestamp(path.stat().st_mtime), None


def parse_auto_backup_interval(raw: str) -> int:
    """Parse and validate Auto Backup interval (minutes). Raises ValueError if invalid."""
    try:
        value = int(str(raw).strip())
    except (TypeError, ValueError) as exc:
        raise ValueError("invalid") from exc
    if value < MIN_AUTO_BACKUP_INTERVAL or value > MAX_AUTO_BACKUP_INTERVAL:
        raise ValueError("invalid")
    return value


def parse_max_backups(raw: str) -> int:
    """Parse and validate Max Backups. Raises ValueError if invalid."""
    try:
        value = int(str(raw).strip())
    except (TypeError, ValueError) as exc:
        raise ValueError("invalid") from exc
    if value < MIN_MAX_BACKUPS or value > MAX_MAX_BACKUPS:
        raise ValueError("invalid")
    return value


def format_auto_backup_lines(workspace: Workspace) -> list[str]:
    """Shared Auto Backup status body for CLI and Telegram."""
    from ...ui.copy import (
        DIVIDER,
        LABEL_INTERVAL,
        LABEL_STATUS,
        STATUS_AUTO_DISABLED,
        STATUS_AUTO_ENABLED,
        TITLE_AUTO_BACKUP,
    )

    enabled = bool(workspace.auto_backup_enabled)
    interval = int(workspace.auto_backup_interval or 0)
    lines = [
        TITLE_AUTO_BACKUP,
        LABEL_STATUS,
        STATUS_AUTO_ENABLED if enabled else STATUS_AUTO_DISABLED,
        LABEL_INTERVAL,
    ]
    if enabled and interval >= MIN_AUTO_BACKUP_INTERVAL:
        unit = "minute" if interval == 1 else "minutes"
        lines.append(f"{interval} {unit}")
    else:
        lines.append("—")
    lines.append(DIVIDER)
    return lines


def format_max_backups_lines(workspace: Workspace) -> list[str]:
    """Shared Max Backups status body for CLI and Telegram."""
    from ...ui.copy import DIVIDER, LABEL_CURRENT_LIMIT, TITLE_MAX_BACKUPS

    return [
        TITLE_MAX_BACKUPS,
        LABEL_CURRENT_LIMIT,
        str(_clamp_max_backups(workspace.max_backups)),
        DIVIDER,
    ]


def _clamp_max_backups(value: int | None) -> int:
    try:
        parsed = int(value if value is not None else DEFAULT_MAX_BACKUPS)
    except (TypeError, ValueError):
        parsed = DEFAULT_MAX_BACKUPS
    return max(MIN_MAX_BACKUPS, min(MAX_MAX_BACKUPS, parsed))


def format_size(num_bytes: int) -> str:
    """Human-readable archive size shared by all interfaces."""
    size = float(num_bytes)
    for unit in ("B", "KB", "MB", "GB"):
        if size < 1024 or unit == "GB":
            return f"{size:.0f} {unit}" if unit == "B" else f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} GB"


def format_duration(seconds: float) -> str:
    return f"{seconds:.1f} sec" if seconds < 1 else f"{seconds:.0f} sec"


def archive_display(archive: BackupArchive) -> tuple[str, str, str]:
    """Return the CLI-equivalent archive name, relative time, and compact size."""
    size = archive.size_bytes
    compact = f"{size:.0f} B" if size < 1024 else (
        f"{size / 1024:.0f} KB" if size < 1024 * 1024 else f"{size / (1024 * 1024):.1f} MB"
    )
    return archive.path.name, relative_time(archive.created_at), compact
