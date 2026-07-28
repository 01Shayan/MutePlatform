"""Operation plugin contract — business logic only; workflow stays in the engine."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Mapping, Sequence

from ....core.workspace import Workspace
from ..models import OperationSummary, PreviewPlan, SelectedUser


class GroupOperation(ABC):
    """Lightweight plugin for one group write operation.

    Implementations must NOT run user selection, confirmation UI, or the shared
    pipeline. They only validate input, build a preview, and execute the action.
    """

    id: str
    label: str
    description: str = ""

    @property
    def available(self) -> bool:
        """False means the operation is registered but not ready (Coming Soon)."""
        return True

    @abstractmethod
    def validate_parameters(
        self, parameters: Mapping[str, Any], users: Sequence[SelectedUser]
    ) -> None:
        """Raise ``GroupEngineError`` (or ValueError) when configuration is invalid."""

    @abstractmethod
    def build_preview(
        self, users: Sequence[SelectedUser], parameters: Mapping[str, Any]
    ) -> PreviewPlan:
        """Return a preview plan. Must not mutate panel state."""

    @abstractmethod
    def execute(
        self,
        users: Sequence[SelectedUser],
        parameters: Mapping[str, Any],
        *,
        workspace: Workspace,
    ) -> OperationSummary:
        """Perform the write. Called only after preview + confirmation by the engine."""
