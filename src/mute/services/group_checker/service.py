"""GroupCheckerApplicationService — interface-facing coordinator for offline group queries."""

from __future__ import annotations

import json

from ...core.history import record_job
from ...core.logging import get_logger
from ...core.workspace import Workspace
from ..backup import BackupApplicationService, format_size
from .engine import GroupCheckerService
from .models import (
    BackupSource,
    GroupCheckerResult,
    GroupQueryDescriptor,
    GroupQueryType,
)
from .queries import build_query
from .reader import BackupReadError

logger = get_logger("group_checker")


class GroupCheckerOperationError(Exception):
    """A safe, interface-ready explanation of a Group Checker failure."""


class GroupCheckerApplicationService:
    """Lists backups, runs queries, returns DTOs, and records history — never exposes engine models."""

    def __init__(
        self,
        *,
        backups: BackupApplicationService | None = None,
        engine: GroupCheckerService | None = None,
    ) -> None:
        self._backups = backups or BackupApplicationService()
        self._engine = engine or GroupCheckerService()

    def list_backups(self, workspace: Workspace) -> list[BackupSource]:
        sources: list[BackupSource] = []
        for archive in self._backups.archives(workspace):
            users = self._users_from_archive(archive.path)
            sources.append(
                BackupSource(
                    name=archive.path.name,
                    created_at=archive.created_at,
                    users=users,
                    size_label=format_size(archive.size_bytes),
                )
            )
        return sources

    def run_query(
        self,
        workspace: Workspace,
        backup_name: str,
        descriptor: GroupQueryDescriptor,
    ) -> GroupCheckerResult:
        if not descriptor.group_ids:
            raise GroupCheckerOperationError("At least one group ID is required.")
        archive = next(
            (item for item in self._backups.archives(workspace) if item.path.name == backup_name),
            None,
        )
        if archive is None:
            raise GroupCheckerOperationError(f"Backup '{backup_name}' was not found.")

        try:
            query = build_query(descriptor.query_type, descriptor.group_ids)
        except ValueError as exc:
            raise GroupCheckerOperationError(str(exc)) from exc

        logger.info(
            "Running %s on '%s' (groups=%s) in workspace '%s'",
            query.label, backup_name, list(descriptor.group_ids), workspace.name,
        )
        try:
            engine_result = self._engine.run(archive.path, query)
        except BackupReadError as exc:
            raise GroupCheckerOperationError(str(exc)) from exc

        result = GroupCheckerResult(
            workspace=workspace.name,
            backup_name=engine_result.snapshot.archive_name,
            backup_created_at=engine_result.snapshot.created_at,
            query_type=query.query_type.value,
            query_label=query.label,
            required_group_ids=descriptor.group_ids,
            total_users=engine_result.total_users,
            matching_users=engine_result.matching_users,
            users=engine_result.users,
            duration_seconds=engine_result.duration_seconds,
        )
        logger.info(
            "Query completed: %d of %d users matched (%.2fs)",
            result.matching_users, result.total_users, result.duration_seconds,
        )
        self._record_history(workspace, result)
        return result

    def _record_history(self, workspace: Workspace, result: GroupCheckerResult) -> None:
        payload = {
            "type": "group_checker",
            "status": "success",
            "workspace": result.workspace,
            "query": result.query_type,
            "required_groups": list(result.required_group_ids),
            "backup": result.backup_name,
            "total_users": result.total_users,
            "matching_users": result.matching_users,
            "matching_usernames": [user.username for user in result.users],
            "duration": round(result.duration_seconds, 1),
        }
        try:
            record_job(payload, jobs_dir=workspace.history_dir)
        except OSError as exc:
            logger.warning("Could not record job history: %s", exc)

    @staticmethod
    def _users_from_archive(path) -> int:
        try:
            meta = json.loads(path.read_text(encoding="utf-8")).get("metadata", {})
            return int(meta.get("users_count") or 0)
        except (json.JSONDecodeError, OSError, TypeError, ValueError):
            return 0


def parse_group_ids(raw: str) -> tuple[int, ...]:
    """Parse a comma/space-separated list of group IDs. Raises ValueError on empty/invalid input."""
    parts = (raw or "").replace(",", " ").split()
    if not parts:
        raise ValueError("Enter at least one numeric group ID (e.g. 1, 3).")
    ids: list[int] = []
    for part in parts:
        try:
            ids.append(int(part))
        except ValueError as exc:
            raise ValueError(f"Invalid group ID '{part}'. Use numbers only (e.g. 1, 3).") from exc
    # Preserve order while removing duplicates.
    seen: set[int] = set()
    unique: list[int] = []
    for value in ids:
        if value not in seen:
            seen.add(value)
            unique.append(value)
    return tuple(unique)


def format_group_ids(ids: tuple[int, ...]) -> str:
    """Human-readable group ID list for summaries and tables."""
    return ", ".join(str(value) for value in ids) if ids else "—"
