"""Group Snapshot — lightweight in-memory user copy for Group Manager only.

Created on enter, destroyed on leave. Never written to disk.
Stores only ``username`` and ``group_ids``. Group Catalog is separate.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Iterable

from ....integrations.pasarguard.client import PasarGuardClient, create_client
from ....core.workspace import Workspace


@dataclass(frozen=True)
class SnapshotUser:
    username: str
    group_ids: tuple[int, ...]


@dataclass
class GroupSnapshot:
    """Immutable for the session lifetime (never refreshed mid-session)."""

    users: tuple[SnapshotUser, ...]
    loaded_at: datetime

    @property
    def user_count(self) -> int:
        return len(self.users)


def load_group_snapshot(workspace: Workspace, *, client: PasarGuardClient | None = None) -> GroupSnapshot:
    """Read panel users into a Group Snapshot (API does no filtering)."""
    api = client or create_client(workspace)
    users = tuple(_project_user(user.username, user.group_ids) for user in api.iter_users())
    return GroupSnapshot(
        users=users,
        loaded_at=datetime.now(timezone.utc).replace(tzinfo=None),
    )


def _project_user(username: str | None, group_ids: Iterable[int] | None) -> SnapshotUser:
    name = (username or "").strip()
    ids: list[int] = []
    for value in group_ids or ():
        try:
            ids.append(int(value))
        except (TypeError, ValueError):
            continue
    return SnapshotUser(username=name, group_ids=tuple(sorted(set(ids))))
