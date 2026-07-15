"""Group-membership query model and registry.

Adding a future query means: implement :class:`GroupQuery`, register it in
:data:`QUERY_REGISTRY`, and expose it in the interfaces — the application service contract
stays ``run_query(workspace, backup_name, descriptor)``.
"""

from __future__ import annotations

from typing import Protocol

from .models import GroupQueryType
from .reader import BackupUser


class GroupQuery(Protocol):
    """A typed, pluggable membership predicate over one backup user."""

    @property
    def query_type(self) -> GroupQueryType: ...

    @property
    def label(self) -> str: ...

    @property
    def group_ids(self) -> tuple[int, ...]: ...

    def evaluate(self, user: BackupUser) -> bool:
        """Return ``True`` when this user belongs in the result set."""


class RequiredGroupsQuery:
    """Return users who do NOT contain all of the required group IDs.

    Mathematically: ``NOT (g1 AND g2 AND …)`` — anyone missing one or more required groups.
    """

    def __init__(self, group_ids: tuple[int, ...]) -> None:
        self._group_ids = tuple(group_ids)

    @property
    def query_type(self) -> GroupQueryType:
        return GroupQueryType.REQUIRED_GROUPS

    @property
    def label(self) -> str:
        return "Required Groups"

    @property
    def group_ids(self) -> tuple[int, ...]:
        return self._group_ids

    def evaluate(self, user: BackupUser) -> bool:
        required = set(self._group_ids)
        current = set(user.group_ids)
        return not required.issubset(current)

    def missing_for(self, user: BackupUser) -> tuple[int, ...]:
        """Return the required group IDs this user is missing, sorted ascending."""
        return tuple(sorted(set(self._group_ids) - set(user.group_ids)))


QUERY_REGISTRY: dict[GroupQueryType, type] = {
    GroupQueryType.REQUIRED_GROUPS: RequiredGroupsQuery,
}


def build_query(query_type: GroupQueryType, group_ids: tuple[int, ...]) -> GroupQuery:
    """Resolve a registry entry into a concrete query instance."""
    cls = QUERY_REGISTRY.get(query_type)
    if cls is None:
        raise ValueError(f"Unknown group query type: {query_type}")
    return cls(group_ids)
