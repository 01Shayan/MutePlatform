"""BackupReader — load a frozen backup JSON and project users to username + group_ids.

Pure file I/O and parsing. No Workspace, no HTTP, no interface knowledge.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from ...core.logging import get_logger

logger = get_logger("group_checker")


class BackupReadError(Exception):
    """Raised when a backup file cannot be loaded or is structurally invalid."""


@dataclass(frozen=True)
class BackupUser:
    """Minimal user projection used by group queries."""

    username: str
    group_ids: tuple[int, ...]


@dataclass(frozen=True)
class BackupSnapshot:
    """An in-memory view of one backup, ready for querying."""

    archive_name: str
    created_at: datetime
    users_count: int
    users: tuple[BackupUser, ...]


class BackupReader:
    """Load and validate a frozen ``{metadata, users}`` backup file."""

    def load(self, path: Path) -> BackupSnapshot:
        path = Path(path)
        if not path.is_file():
            raise BackupReadError(f"Backup file not found: {path.name}")
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as exc:
            raise BackupReadError(f"Could not read backup '{path.name}': {exc}") from exc
        if not isinstance(payload, dict):
            raise BackupReadError(f"Backup '{path.name}' is not a JSON object.")
        if "metadata" not in payload or "users" not in payload:
            raise BackupReadError(
                f"Backup '{path.name}' is missing required top-level keys (metadata, users)."
            )
        users_raw = payload["users"]
        if not isinstance(users_raw, list):
            raise BackupReadError(f"Backup '{path.name}' has an invalid users list.")

        users = tuple(self._project_users(users_raw, path.name))
        metadata = payload.get("metadata") if isinstance(payload.get("metadata"), dict) else {}
        created_at = self._created_at(metadata, path)
        users_count = self._users_count(metadata, len(users))
        return BackupSnapshot(
            archive_name=path.name,
            created_at=created_at,
            users_count=users_count,
            users=users,
        )

    def _project_users(self, entries: list, archive_name: str) -> list[BackupUser]:
        projected: list[BackupUser] = []
        for index, entry in enumerate(entries):
            if not isinstance(entry, dict):
                logger.warning(
                    "Skipping malformed user entry #%d in '%s' (not an object).",
                    index, archive_name,
                )
                continue
            username = entry.get("username")
            if not isinstance(username, str) or not username.strip():
                logger.warning(
                    "Skipping malformed user entry #%d in '%s' (missing username).",
                    index, archive_name,
                )
                continue
            group_ids = self._normalize_group_ids(entry.get("group_ids"), archive_name, username)
            projected.append(BackupUser(username=username.strip(), group_ids=group_ids))
        return projected

    @staticmethod
    def _normalize_group_ids(raw, archive_name: str, username: str) -> tuple[int, ...]:
        if raw is None:
            return ()
        if not isinstance(raw, list):
            logger.warning(
                "User '%s' in '%s' has non-list group_ids; treating as empty.",
                username, archive_name,
            )
            return ()
        result: list[int] = []
        for value in raw:
            try:
                result.append(int(value))
            except (TypeError, ValueError):
                logger.warning(
                    "User '%s' in '%s' has non-integer group id %r; skipping that id.",
                    username, archive_name, value,
                )
        return tuple(result)

    @staticmethod
    def _created_at(metadata: dict, path: Path) -> datetime:
        raw = metadata.get("created_at")
        if isinstance(raw, str):
            try:
                return datetime.fromisoformat(raw)
            except ValueError:
                pass
        try:
            return datetime.fromtimestamp(path.stat().st_mtime)
        except OSError:
            return datetime.now()

    @staticmethod
    def _users_count(metadata: dict, fallback: int) -> int:
        raw = metadata.get("users_count")
        try:
            return int(raw) if raw is not None else fallback
        except (TypeError, ValueError):
            return fallback
