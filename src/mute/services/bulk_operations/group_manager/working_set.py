"""Working Set — Query result held in memory for Actions."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .query import GroupQuery


@dataclass(frozen=True)
class WorkingSetUser:
    username: str
    group_ids: tuple[int, ...]


@dataclass(frozen=True)
class WorkingSet:
    """Matched users from the latest Query. Regenerated when Query changes."""

    users: tuple[WorkingSetUser, ...]
    query: "GroupQuery"
    total_in_snapshot: int

    @property
    def matched(self) -> int:
        return len(self.users)

    def usernames(self) -> tuple[str, ...]:
        return tuple(user.username for user in self.users)
