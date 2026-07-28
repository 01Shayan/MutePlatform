"""Action plugin contract — operate on an existing Working Set only."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Mapping

from .....core.workspace import Workspace
from ..working_set import WorkingSet


@dataclass(frozen=True)
class ActionInfo:
    """Menu-safe description of a registered action."""

    id: str
    label: str
    available: bool
    description: str = ""


@dataclass(frozen=True)
class ActionSummary:
    """Outcome of a successful action execution."""

    action_id: str
    action_label: str
    user_count: int
    message: str = ""
    details: tuple[str, ...] = ()


class GroupAction(ABC):
    """Lightweight plugin. Must not search users — only consume the Working Set."""

    id: str
    label: str
    description: str = ""

    @property
    def available(self) -> bool:
        return True

    @abstractmethod
    def validate_parameters(self, parameters: Mapping[str, Any], working_set: WorkingSet) -> None:
        """Raise GroupManagerError / ValueError when configuration is invalid."""

    @abstractmethod
    def execute(
        self,
        working_set: WorkingSet,
        parameters: Mapping[str, Any],
        *,
        workspace: Workspace,
    ) -> ActionSummary:
        """Apply the modification to the Working Set's matched users."""
