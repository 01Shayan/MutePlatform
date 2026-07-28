"""GroupEngineApplicationService — interface-facing coordinator for the write workflow."""

from __future__ import annotations

from typing import Any, Mapping, Sequence

from ...core.logging import get_logger
from ...core.workspace import Workspace
from ..backup import BackupApplicationService
from ..group_checker.reader import BackupReadError, BackupReader
from .errors import GroupEngineError
from .models import OperationInfo, OperationSummary, PreviewPlan, SelectedUser, WorkflowStage
from .operations import GroupOperation
from .session import GroupEngineSession
from .workflow import GroupWorkflowEngine

logger = get_logger("group_engine")

DEFAULT_SESSION_KEY = "default"


class GroupEngineApplicationService:
    """Owns session lifecycle and exposes the shared write pipeline to every interface.

    Check remains on ``GroupCheckerApplicationService``. This service never duplicates
    preview / confirmation / execution flow inside individual operations.

    ``session_key`` isolates concurrent sessions (CLI uses the default; Telegram uses
    the chat id).
    """

    def __init__(
        self,
        *,
        engine: GroupWorkflowEngine | None = None,
        backups: BackupApplicationService | None = None,
        reader: BackupReader | None = None,
    ) -> None:
        self._engine = engine or GroupWorkflowEngine()
        self._backups = backups or BackupApplicationService()
        self._reader = reader or BackupReader()

    # -- session ----------------------------------------------------------------------

    def begin_session(
        self, workspace: Workspace, *, session_key: str = DEFAULT_SESSION_KEY
    ) -> GroupEngineSession:
        session = self._engine.begin(workspace.name, key=session_key)
        logger.info(
            "Group Engine session started for workspace '%s' (key=%s)",
            workspace.name,
            session_key,
        )
        return session

    def session(self, *, session_key: str = DEFAULT_SESSION_KEY) -> GroupEngineSession | None:
        return self._engine.session(key=session_key)

    def require_session(self, *, session_key: str = DEFAULT_SESSION_KEY) -> GroupEngineSession:
        return self._engine.require_session(key=session_key)

    def leave_session(self, *, session_key: str = DEFAULT_SESSION_KEY) -> None:
        if self._engine.session(key=session_key) is not None:
            logger.info("Group Engine session closed (key=%s)", session_key)
        self._engine.leave(key=session_key)

    def ensure_session(
        self, workspace: Workspace, *, session_key: str = DEFAULT_SESSION_KEY
    ) -> GroupEngineSession:
        """Return the active session, or start one for this workspace."""
        current = self.session(session_key=session_key)
        if current is not None and current.workspace_name == workspace.name:
            return current
        return self.begin_session(workspace, session_key=session_key)

    # -- catalogue --------------------------------------------------------------------

    def list_operations(self) -> list[OperationInfo]:
        return self._engine.list_operations()

    def operation(self, operation_id: str) -> OperationInfo:
        op = self._engine.get_operation(operation_id)
        return OperationInfo(
            id=op.id,
            label=op.label,
            available=op.available,
            description=op.description,
        )

    # -- user selection ---------------------------------------------------------------

    def list_backup_users(self, workspace: Workspace, backup_name: str) -> list[SelectedUser]:
        """Load username + group_ids from a backup for selection menus."""
        archive = next(
            (item for item in self._backups.archives(workspace) if item.path.name == backup_name),
            None,
        )
        if archive is None:
            raise GroupEngineError(f"Backup '{backup_name}' was not found.")
        try:
            snapshot = self._reader.load(archive.path)
        except BackupReadError as exc:
            raise GroupEngineError(str(exc)) from exc
        return [
            SelectedUser(username=user.username, group_ids=user.group_ids)
            for user in snapshot.users
        ]

    def set_selected_users(
        self,
        users: Sequence[SelectedUser],
        *,
        backup_name: str | None = None,
        session_key: str = DEFAULT_SESSION_KEY,
    ) -> GroupEngineSession:
        if not users:
            return self._engine.clear_selected_users(key=session_key)
        session = self._engine.set_selected_users(
            users, backup_name=backup_name, key=session_key
        )
        logger.info(
            "Group Engine selection set: %d user(s) from %s",
            session.selected_count,
            backup_name or "manual",
        )
        return session

    def select_users_by_username(
        self,
        workspace: Workspace,
        backup_name: str,
        usernames: Sequence[str],
        *,
        session_key: str = DEFAULT_SESSION_KEY,
    ) -> GroupEngineSession:
        """Resolve usernames against a backup and store them in the session."""
        available = {
            user.username: user for user in self.list_backup_users(workspace, backup_name)
        }
        selected: list[SelectedUser] = []
        missing: list[str] = []
        seen: set[str] = set()
        for raw in usernames:
            name = (raw or "").strip()
            if not name or name in seen:
                continue
            seen.add(name)
            user = available.get(name)
            if user is None:
                missing.append(name)
            else:
                selected.append(user)
        if missing:
            raise GroupEngineError("Unknown username(s) in backup: " + ", ".join(missing))
        if not selected:
            raise GroupEngineError("Select at least one user.")
        return self.set_selected_users(
            selected, backup_name=backup_name, session_key=session_key
        )

    def select_all_users_from_backup(
        self,
        workspace: Workspace,
        backup_name: str,
        *,
        session_key: str = DEFAULT_SESSION_KEY,
    ) -> GroupEngineSession:
        users = self.list_backup_users(workspace, backup_name)
        if not users:
            raise GroupEngineError("This backup has no users to select.")
        return self.set_selected_users(
            users, backup_name=backup_name, session_key=session_key
        )

    def clear_selected_users(
        self, *, session_key: str = DEFAULT_SESSION_KEY
    ) -> GroupEngineSession:
        return self._engine.clear_selected_users(key=session_key)

    # -- write pipeline ---------------------------------------------------------------

    def select_operation(
        self, operation_id: str, *, session_key: str = DEFAULT_SESSION_KEY
    ) -> GroupEngineSession:
        return self._engine.select_operation(operation_id, key=session_key)

    def configure(
        self, parameters: Mapping[str, Any], *, session_key: str = DEFAULT_SESSION_KEY
    ) -> GroupEngineSession:
        return self._engine.configure(parameters, key=session_key)

    def build_preview(self, *, session_key: str = DEFAULT_SESSION_KEY) -> PreviewPlan:
        return self._engine.build_preview(key=session_key)

    def execute(
        self, workspace: Workspace, *, session_key: str = DEFAULT_SESSION_KEY
    ) -> OperationSummary:
        summary = self._engine.execute(workspace, key=session_key)
        logger.info(
            "Group Engine operation '%s' completed for %d user(s)",
            summary.operation_id,
            summary.user_count,
        )
        return summary

    def cancel_operation(
        self, *, session_key: str = DEFAULT_SESSION_KEY
    ) -> GroupEngineSession:
        return self._engine.cancel_operation(key=session_key)

    def stage(self, *, session_key: str = DEFAULT_SESSION_KEY) -> WorkflowStage:
        session = self._engine.session(key=session_key)
        return session.stage if session is not None else WorkflowStage.IDLE

    # -- testing helpers --------------------------------------------------------------

    def register_operation(self, operation: GroupOperation) -> None:
        """Replace or add an operation plugin (used by tests / future wiring)."""
        self._engine._operations[operation.id] = operation  # noqa: SLF001
