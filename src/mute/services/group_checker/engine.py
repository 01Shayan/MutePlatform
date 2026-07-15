"""GroupCheckerService — pure offline query engine over a backup snapshot."""

from __future__ import annotations

import time
from dataclasses import dataclass
from pathlib import Path

from .models import GroupCheckerUserResult
from .queries import GroupQuery
from .reader import BackupReader, BackupSnapshot


@dataclass(frozen=True)
class EngineQueryResult:
    """Engine-level outcome; the application service maps this into public DTOs."""

    snapshot: BackupSnapshot
    query: GroupQuery
    users: tuple[GroupCheckerUserResult, ...]
    duration_seconds: float

    @property
    def total_users(self) -> int:
        return self.snapshot.users_count

    @property
    def matching_users(self) -> int:
        return len(self.users)


class GroupCheckerService:
    """Load a backup, execute a query, and build a result — no Workspace or UI."""

    def __init__(self, reader: BackupReader | None = None) -> None:
        self._reader = reader or BackupReader()

    def run(self, path: Path, query: GroupQuery) -> EngineQueryResult:
        started = time.perf_counter()
        snapshot = self._reader.load(path)
        rows = self._execute(snapshot, query)
        duration = time.perf_counter() - started
        return EngineQueryResult(
            snapshot=snapshot,
            query=query,
            users=tuple(rows),
            duration_seconds=duration,
        )

    def _execute(self, snapshot: BackupSnapshot, query: GroupQuery) -> list[GroupCheckerUserResult]:
        rows: list[GroupCheckerUserResult] = []
        required = set(query.group_ids)
        for user in snapshot.users:
            if not query.evaluate(user):
                continue
            rows.append(
                GroupCheckerUserResult(
                    username=user.username,
                    current_group_ids=tuple(sorted(user.group_ids)),
                    missing_group_ids=tuple(sorted(required - set(user.group_ids))),
                )
            )
        return rows
