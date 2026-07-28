"""Public DTOs for the Group Engine workflow — the only types interfaces should consume."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Mapping


class WorkflowStage(str, Enum):
    """Stages of the shared write pipeline. The engine advances; operations do not."""

    IDLE = "idle"
    SELECT_USERS = "select_users"
    CHOOSE_OPERATION = "choose_operation"
    CONFIGURE = "configure"
    PREVIEW = "preview"
    CONFIRM = "confirm"
    EXECUTE = "execute"
    SUMMARY = "summary"


@dataclass(frozen=True)
class SelectedUser:
    """One user held in the engine session for write operations."""

    username: str
    group_ids: tuple[int, ...] = ()


@dataclass(frozen=True)
class OperationInfo:
    """Menu-safe description of a registered operation plugin."""

    id: str
    label: str
    available: bool
    description: str = ""


@dataclass(frozen=True)
class PreviewPlan:
    """Read-only preview produced before confirmation. Never mutates the panel."""

    operation_id: str
    operation_label: str
    user_count: int
    usernames: tuple[str, ...]
    parameters: Mapping[str, Any]
    lines: tuple[str, ...] = ()


@dataclass(frozen=True)
class OperationSummary:
    """Outcome of a successful execute step."""

    operation_id: str
    operation_label: str
    user_count: int
    usernames: tuple[str, ...]
    parameters: Mapping[str, Any] = field(default_factory=dict)
    message: str = ""
    details: tuple[str, ...] = ()
