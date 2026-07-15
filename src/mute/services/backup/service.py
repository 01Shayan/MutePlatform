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
from ...core.workspace import Workspace
from ...integrations.pasarguard.backup import LATEST_FILENAME, BackupService, LatestBackup, latest_backup
from ...integrations.pasarguard.client import PasarGuardError, create_client


class BackupOperationError(Exception):
    """A safe, interface-ready explanation of a backup operation failure."""


logger = get_logger("backup")


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


@dataclass(frozen=True)
class BackupDownload:
    filename: str
    content: bytes


class BackupApplicationService:
    """Coordinates export, archive inspection, and archive deletion for one workspace."""

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
        return summary

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
        return [BackupArchive(path, self._created_at(path), path.stat().st_size) for path in paths]

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
    def _created_at(path: Path) -> datetime:
        try:
            metadata = json.loads(path.read_text(encoding="utf-8")).get("metadata", {})
            return datetime.fromisoformat(metadata["created_at"])
        except (json.JSONDecodeError, OSError, KeyError, ValueError):
            return datetime.fromtimestamp(path.stat().st_mtime)


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
