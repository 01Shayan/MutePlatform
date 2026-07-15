"""Group Checker DTOs — the only types interfaces may consume.

Engine-internal models (BackupUser, BackupSnapshot) stay inside the package and are never
exported through the application service.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum


class GroupQueryType(str, Enum):
    """Supported group-membership queries. Extend by adding a value and a registry entry."""

    REQUIRED_GROUPS = "required_groups"


@dataclass(frozen=True)
class BackupSource:
    """A backup available for querying — safe for menus."""

    name: str
    created_at: datetime
    users: int
    size_label: str


@dataclass(frozen=True)
class GroupQueryDescriptor:
    """What an interface sends to the application service to run a query."""

    query_type: GroupQueryType
    group_ids: tuple[int, ...]


@dataclass(frozen=True)
class GroupCheckerUserResult:
    """One user in the query result set."""

    username: str
    current_group_ids: tuple[int, ...]
    missing_group_ids: tuple[int, ...]


@dataclass(frozen=True)
class GroupCheckerResult:
    """Complete query outcome returned to every interface."""

    workspace: str
    backup_name: str
    backup_created_at: datetime
    query_type: str
    query_label: str
    required_group_ids: tuple[int, ...]
    total_users: int
    matching_users: int
    users: tuple[GroupCheckerUserResult, ...]
    duration_seconds: float
