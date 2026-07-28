"""Remove Group IDs action."""

from __future__ import annotations

from typing import Any, Mapping

from .....core.workspace import Workspace
from ..errors import GroupManagerError
from ..working_set import WorkingSet
from .base import ActionSummary, GroupAction


class RemoveGroupIdsAction(GroupAction):
    id = "remove"
    label = "Remove Group IDs"
    description = "Remove group IDs from every matched user in the current Working Set."
    available = False

    def validate_parameters(self, parameters: Mapping[str, Any], working_set: WorkingSet) -> None:
        raise GroupManagerError(f"{self.label} is coming soon.")

    def execute(
        self,
        working_set: WorkingSet,
        parameters: Mapping[str, Any],
        *,
        workspace: Workspace,
    ) -> ActionSummary:
        raise GroupManagerError(f"{self.label} is coming soon.")
