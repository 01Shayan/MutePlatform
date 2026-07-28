"""Check — inspect users from a backup and build a Working Set. Never mutates users."""

from __future__ import annotations

import json
import time

from ....core.history import record_job
from ....core.logging import get_logger
from ....core.workspace import Workspace
from ...backup import BackupApplicationService, format_size
from ...group_checker.engine import GroupCheckerService
from ...group_checker.models import BackupSource, GroupQueryDescriptor, GroupQueryType
from ...group_checker.queries import build_query
from ...group_checker.reader import BackupReadError
from ...group_checker.service import format_group_ids, parse_group_ids
from .errors import GroupManagerError
from .working_set import CheckCriteria, WorkingSet, WorkingSetUser

logger = get_logger("group_manager")


class GroupChecker:
    """Runs the existing Required Groups check and materializes a Working Set."""

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

    def run(
        self,
        workspace: Workspace,
        backup_name: str,
        descriptor: GroupQueryDescriptor,
    ) -> WorkingSet:
        if not descriptor.group_ids:
            raise GroupManagerError("At least one group ID is required.")
        archive = next(
            (item for item in self._backups.archives(workspace) if item.path.name == backup_name),
            None,
        )
        if archive is None:
            raise GroupManagerError(f"Backup '{backup_name}' was not found.")

        try:
            query = build_query(descriptor.query_type, descriptor.group_ids)
        except ValueError as exc:
            raise GroupManagerError(str(exc)) from exc

        logger.info(
            "Running %s on '%s' (groups=%s) in workspace '%s'",
            query.label,
            backup_name,
            list(descriptor.group_ids),
            workspace.name,
        )
        started = time.perf_counter()
        try:
            engine_result = self._engine.run(archive.path, query)
        except BackupReadError as exc:
            raise GroupManagerError(str(exc)) from exc
        # Prefer wall time around the same engine call path used historically.
        duration = engine_result.duration_seconds or (time.perf_counter() - started)

        required = set(descriptor.group_ids)
        matched_names = {row.username for row in engine_result.users}
        matched = tuple(
            WorkingSetUser(
                username=row.username,
                current_group_ids=row.current_group_ids,
                missing_group_ids=row.missing_group_ids,
            )
            for row in engine_result.users
        )
        unmatched = tuple(
            WorkingSetUser(
                username=user.username,
                current_group_ids=tuple(sorted(user.group_ids)),
                missing_group_ids=tuple(sorted(required - set(user.group_ids))),
            )
            for user in engine_result.snapshot.users
            if user.username not in matched_names
        )

        working_set = WorkingSet(
            workspace=workspace.name,
            backup_name=engine_result.snapshot.archive_name,
            backup_created_at=engine_result.snapshot.created_at,
            criteria=CheckCriteria(
                query_type=query.query_type.value,
                query_label=query.label,
                required_group_ids=descriptor.group_ids,
            ),
            matched_users=matched,
            unmatched_users=unmatched,
            total_users=engine_result.total_users,
            duration_seconds=duration,
        )
        logger.info(
            "Check completed: %d matched, %d unmatched of %d (%.2fs)",
            working_set.matched_count,
            working_set.unmatched_count,
            working_set.total_users,
            working_set.duration_seconds,
        )
        self._record_history(workspace, working_set)
        return working_set

    def _record_history(self, workspace: Workspace, working_set: WorkingSet) -> None:
        payload = {
            "type": "group_checker",
            "status": "success",
            "workspace": working_set.workspace,
            "query": working_set.criteria.query_type,
            "required_groups": list(working_set.required_group_ids),
            "backup": working_set.backup_name,
            "total_users": working_set.total_users,
            "matching_users": working_set.matched_count,
            "matching_usernames": [user.username for user in working_set.matched_users],
            "duration": round(working_set.duration_seconds, 1),
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


# Re-export helpers so interfaces can import Check utilities from Group Manager.
__all__ = [
    "GroupChecker",
    "GroupQueryDescriptor",
    "GroupQueryType",
    "BackupSource",
    "format_group_ids",
    "parse_group_ids",
]
