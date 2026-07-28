"""Group Manager session — holds the current Working Set until the user leaves."""

from __future__ import annotations

from dataclasses import dataclass

from .working_set import WorkingSet


@dataclass
class GroupManagerSession:
    """One visit to Group Manager. Cleared when leaving Bulk Operations / Group Manager."""

    workspace_name: str
    working_set: WorkingSet | None = None

    @property
    def has_working_set(self) -> bool:
        return self.working_set is not None
