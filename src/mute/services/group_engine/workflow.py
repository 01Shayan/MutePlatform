"""Stateful workflow orchestrator — owns the shared write pipeline once.

Select Users → Choose Operation → Configure → Preview → Confirm → Execute → Summary
"""

from __future__ import annotations

from typing import Any, Mapping, Sequence

from ...core.workspace import Workspace
from .errors import GroupEngineError
from .models import OperationInfo, OperationSummary, PreviewPlan, SelectedUser, WorkflowStage
from .operations import GroupOperation, default_operations
from .session import GroupEngineSession


class GroupWorkflowEngine:
    """Session + pipeline manager. Operations never own these steps."""

    def __init__(self, operations: Sequence[GroupOperation] | None = None) -> None:
        ops = tuple(operations) if operations is not None else default_operations()
        self._operations: dict[str, GroupOperation] = {op.id: op for op in ops}
        self._sessions: dict[str, GroupEngineSession] = {}

    # -- session lifecycle ------------------------------------------------------------

    def begin(self, workspace_name: str, *, key: str = "default") -> GroupEngineSession:
        session = GroupEngineSession(
            workspace_name=workspace_name,
            stage=WorkflowStage.SELECT_USERS,
        )
        self._sessions[key] = session
        return session

    def session(self, *, key: str = "default") -> GroupEngineSession | None:
        return self._sessions.get(key)

    def require_session(self, *, key: str = "default") -> GroupEngineSession:
        session = self._sessions.get(key)
        if session is None:
            raise GroupEngineError("No active Group Engine session. Enter Group Engine first.")
        return session

    def leave(self, *, key: str = "default") -> None:
        """Clear the session for this key — only when leaving Group Engine."""
        self._sessions.pop(key, None)

    # -- operations catalogue ---------------------------------------------------------

    def list_operations(self) -> list[OperationInfo]:
        return [
            OperationInfo(
                id=op.id,
                label=op.label,
                available=op.available,
                description=op.description,
            )
            for op in self._operations.values()
        ]

    def get_operation(self, operation_id: str) -> GroupOperation:
        try:
            return self._operations[operation_id]
        except KeyError as exc:
            raise GroupEngineError(f"Unknown operation '{operation_id}'.") from exc

    # -- user selection ---------------------------------------------------------------

    def set_selected_users(
        self,
        users: Sequence[SelectedUser],
        *,
        backup_name: str | None = None,
        key: str = "default",
    ) -> GroupEngineSession:
        session = self.require_session(key=key)
        selected = tuple(users)
        session.selected_users = selected
        session.backup_name = backup_name
        self._clear_operation_state(session)
        session.stage = (
            WorkflowStage.CHOOSE_OPERATION if selected else WorkflowStage.SELECT_USERS
        )
        return session

    def clear_selected_users(self, *, key: str = "default") -> GroupEngineSession:
        return self.set_selected_users((), backup_name=None, key=key)

    # -- operation pipeline -----------------------------------------------------------

    def select_operation(self, operation_id: str, *, key: str = "default") -> GroupEngineSession:
        session = self.require_session(key=key)
        if not session.has_selection:
            raise GroupEngineError("Select users before choosing an operation.")
        operation = self.get_operation(operation_id)
        if not operation.available:
            raise GroupEngineError(f"{operation.label} is coming soon.")
        self._clear_operation_state(session)
        session.operation_id = operation.id
        session.stage = WorkflowStage.CONFIGURE
        return session

    def configure(
        self, parameters: Mapping[str, Any], *, key: str = "default"
    ) -> GroupEngineSession:
        session = self.require_session(key=key)
        operation = self._require_operation(session)
        params = dict(parameters)
        try:
            operation.validate_parameters(params, session.selected_users)
        except ValueError as exc:
            raise GroupEngineError(str(exc)) from exc
        session.parameters = params
        session.preview = None
        session.stage = WorkflowStage.PREVIEW
        return session

    def build_preview(self, *, key: str = "default") -> PreviewPlan:
        session = self.require_session(key=key)
        operation = self._require_operation(session)
        try:
            preview = operation.build_preview(session.selected_users, session.parameters)
        except ValueError as exc:
            raise GroupEngineError(str(exc)) from exc
        session.preview = preview
        session.stage = WorkflowStage.CONFIRM
        return preview

    def execute(self, workspace: Workspace, *, key: str = "default") -> OperationSummary:
        session = self.require_session(key=key)
        operation = self._require_operation(session)
        if session.preview is None:
            raise GroupEngineError("Build and confirm a preview before executing.")
        if workspace.name != session.workspace_name:
            raise GroupEngineError("Workspace mismatch for the active Group Engine session.")
        session.stage = WorkflowStage.EXECUTE
        try:
            summary = operation.execute(
                session.selected_users,
                session.parameters,
                workspace=workspace,
            )
        except ValueError as exc:
            raise GroupEngineError(str(exc)) from exc
        session.last_summary_message = summary.message or summary.operation_label
        session.stage = WorkflowStage.SUMMARY
        self._clear_operation_state(session, keep_summary=True)
        session.stage = WorkflowStage.CHOOSE_OPERATION
        return summary

    def cancel_operation(self, *, key: str = "default") -> GroupEngineSession:
        """Abort the current operation but keep the user selection."""
        session = self.require_session(key=key)
        self._clear_operation_state(session)
        session.stage = (
            WorkflowStage.CHOOSE_OPERATION if session.has_selection else WorkflowStage.SELECT_USERS
        )
        return session

    # -- internals --------------------------------------------------------------------

    def _require_operation(self, session: GroupEngineSession) -> GroupOperation:
        if not session.operation_id:
            raise GroupEngineError("No operation selected.")
        return self.get_operation(session.operation_id)

    @staticmethod
    def _clear_operation_state(
        session: GroupEngineSession, *, keep_summary: bool = False
    ) -> None:
        session.operation_id = None
        session.parameters = {}
        session.preview = None
        if not keep_summary:
            session.last_summary_message = None
