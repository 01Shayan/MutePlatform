"""Stub write operations — registered so the engine owns their place in the menu."""

from __future__ import annotations

from typing import Any, Mapping, Sequence

from ....core.workspace import Workspace
from ..errors import GroupEngineError
from ..models import OperationSummary, PreviewPlan, SelectedUser
from .base import GroupOperation


class _UnavailableOperation(GroupOperation):
    """Base for Coming Soon plugins."""

    available = False

    def validate_parameters(
        self, parameters: Mapping[str, Any], users: Sequence[SelectedUser]
    ) -> None:
        raise GroupEngineError(f"{self.label} is coming soon.")

    def build_preview(
        self, users: Sequence[SelectedUser], parameters: Mapping[str, Any]
    ) -> PreviewPlan:
        raise GroupEngineError(f"{self.label} is coming soon.")

    def execute(
        self,
        users: Sequence[SelectedUser],
        parameters: Mapping[str, Any],
        *,
        workspace: Workspace,
    ) -> OperationSummary:
        raise GroupEngineError(f"{self.label} is coming soon.")


class AddGroupsOperation(_UnavailableOperation):
    id = "add"
    label = "Add"
    description = (
        "Add groups to selected users. "
        "Follows Select → Preview → Confirmation → Execute → Summary."
    )


class RemoveGroupsOperation(_UnavailableOperation):
    id = "remove"
    label = "Remove"
    description = (
        "Remove groups from selected users. "
        "Follows Select → Preview → Confirmation → Execute → Summary."
    )


class ReplaceGroupsOperation(_UnavailableOperation):
    id = "replace"
    label = "Replace"
    description = (
        "Replace group membership for selected users. "
        "Follows Select → Preview → Confirmation → Execute → Summary."
    )


def default_operations() -> tuple[GroupOperation, ...]:
    return (
        AddGroupsOperation(),
        RemoveGroupsOperation(),
        ReplaceGroupsOperation(),
    )
