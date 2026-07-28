"""Group Query — runs only against a Group Snapshot. Never calls the Panel API."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from .snapshot import GroupSnapshot, SnapshotUser
from .working_set import WorkingSet, WorkingSetUser


class MatchMode(str, Enum):
    ANY = "any"
    ALL = "all"


@dataclass(frozen=True)
class GroupQuery:
    """Include / Exclude group filters with a shared match mode."""

    include_group_ids: tuple[int, ...] = ()
    exclude_group_ids: tuple[int, ...] = ()
    match_mode: MatchMode = MatchMode.ANY

    def to_dict(self) -> dict:
        return {
            "include_group_ids": list(self.include_group_ids),
            "exclude_group_ids": list(self.exclude_group_ids),
            "match_mode": self.match_mode.value,
        }


def execute_query(snapshot: GroupSnapshot, query: GroupQuery) -> WorkingSet:
    """Build a Working Set from Snapshot + Query. Regenerated whenever Query changes."""
    matched = tuple(
        WorkingSetUser(username=user.username, group_ids=user.group_ids)
        for user in snapshot.users
        if user.username and _matches(user, query)
    )
    return WorkingSet(users=matched, query=query, total_in_snapshot=snapshot.user_count)


def _matches(user: SnapshotUser, query: GroupQuery) -> bool:
    current = set(user.group_ids)
    if query.include_group_ids and not _match_set(
        current, set(query.include_group_ids), query.match_mode
    ):
        return False
    if query.exclude_group_ids and _match_set(
        current, set(query.exclude_group_ids), query.match_mode
    ):
        return False
    return True


def _match_set(current: set[int], target: set[int], mode: MatchMode) -> bool:
    if not target:
        return True
    if mode is MatchMode.ALL:
        return target.issubset(current)
    return bool(current & target)
