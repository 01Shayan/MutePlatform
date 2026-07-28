"""Action plugin contract — operate on an existing Working Set only."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Mapping, Sequence

from ..working_set import WorkingSetUser


@dataclass(frozen=True)
class ActionInfo:
    id: str
    label: str
    available: bool
    description: str = ""


@dataclass(frozen=True)
class PlannedChange:
    username: str
    before: tuple[int, ...]
    after: tuple[int, ...]


class GroupAction(ABC):
    """Lightweight plugin. Must not search users — only consume the Working Set."""

    id: str
    label: str
    description: str = ""
    report_action: str = ""

    @property
    def available(self) -> bool:
        return True

    @abstractmethod
    def validate_parameters(self, parameters: Mapping[str, Any]) -> tuple[int, ...]:
        """Return validated group IDs for the action."""

    @abstractmethod
    def plan(
        self, users: Sequence[WorkingSetUser], group_ids: Sequence[int]
    ) -> list[PlannedChange]:
        """Compute per-user before/after group membership. No Panel calls."""
