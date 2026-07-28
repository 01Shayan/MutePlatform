"""Mutable Group Engine session — lives until the user leaves the engine."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .models import PreviewPlan, SelectedUser, WorkflowStage


@dataclass
class GroupEngineSession:
    """Reusable session for one visit to the Group Engine.

    Selected users persist across completed operations. Leaving the engine clears
    the session entirely.
    """

    workspace_name: str
    selected_users: tuple[SelectedUser, ...] = ()
    backup_name: str | None = None
    operation_id: str | None = None
    parameters: dict[str, Any] = field(default_factory=dict)
    preview: PreviewPlan | None = None
    stage: WorkflowStage = WorkflowStage.IDLE
    last_summary_message: str | None = None

    @property
    def selected_count(self) -> int:
        return len(self.selected_users)

    @property
    def has_selection(self) -> bool:
        return bool(self.selected_users)

    def usernames(self) -> tuple[str, ...]:
        return tuple(user.username for user in self.selected_users)
