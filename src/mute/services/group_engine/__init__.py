"""Group Engine — reusable stateful workflow for group write operations.

Check (read-only analysis) stays in ``group_checker``. Write operations plug into
this package as lightweight plugins; the engine owns session, selection, preview,
confirmation, execution, and summary.
"""

from .errors import GroupEngineError
from .models import (
    OperationInfo,
    OperationSummary,
    PreviewPlan,
    SelectedUser,
    WorkflowStage,
)
from .operations import GroupOperation
from .service import GroupEngineApplicationService
from .session import GroupEngineSession

__all__ = [
    "GroupEngineApplicationService",
    "GroupEngineError",
    "GroupEngineSession",
    "GroupOperation",
    "OperationInfo",
    "OperationSummary",
    "PreviewPlan",
    "SelectedUser",
    "WorkflowStage",
]
