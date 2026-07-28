"""Working Set — the only user set Actions may consume.

Produced exclusively by Check. Never built by manual selection.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class CheckCriteria:
    """Search criteria that produced this Working Set."""

    query_type: str
    query_label: str
    required_group_ids: tuple[int, ...]


@dataclass(frozen=True)
class WorkingSetUser:
    """One user projected into the Working Set."""

    username: str
    current_group_ids: tuple[int, ...]
    missing_group_ids: tuple[int, ...] = ()


@dataclass(frozen=True)
class WorkingSet:
    """Immutable Check outcome: matched / unmatched users plus statistics and criteria."""

    workspace: str
    backup_name: str
    backup_created_at: datetime
    criteria: CheckCriteria
    matched_users: tuple[WorkingSetUser, ...]
    unmatched_users: tuple[WorkingSetUser, ...]
    total_users: int
    duration_seconds: float

    @property
    def matched_count(self) -> int:
        return len(self.matched_users)

    @property
    def unmatched_count(self) -> int:
        return len(self.unmatched_users)

    @property
    def required_group_ids(self) -> tuple[int, ...]:
        return self.criteria.required_group_ids

    @property
    def query_label(self) -> str:
        return self.criteria.query_label
