"""GroupManagerApplicationService — interface-facing coordinator for Group Manager."""

from __future__ import annotations

from typing import Any, Mapping, Sequence

from ....core.logging import get_logger
from ....core.workspace import Workspace
from ...group_checker.models import BackupSource, GroupQueryDescriptor
from .actions import ActionInfo, ActionSummary, GroupAction, default_actions
from .checker import GroupChecker
from .errors import GroupManagerError
from .session import GroupManagerSession
from .working_set import WorkingSet

logger = get_logger("group_manager")

DEFAULT_SESSION_KEY = "default"


class GroupManagerApplicationService:
    """Owns the Group Manager session: Check → Working Set → Actions.

    Actions never search. They only consume the Working Set produced by Check.
    """

    def __init__(
        self,
        *,
        checker: GroupChecker | None = None,
        actions: Sequence[GroupAction] | None = None,
    ) -> None:
        self._checker = checker or GroupChecker()
        ops = tuple(actions) if actions is not None else default_actions()
        self._actions: dict[str, GroupAction] = {action.id: action for action in ops}
        self._sessions: dict[str, GroupManagerSession] = {}

    # -- session ----------------------------------------------------------------------

    def begin_session(
        self, workspace: Workspace, *, session_key: str = DEFAULT_SESSION_KEY
    ) -> GroupManagerSession:
        session = GroupManagerSession(workspace_name=workspace.name)
        self._sessions[session_key] = session
        logger.info(
            "Group Manager session started for workspace '%s' (key=%s)",
            workspace.name,
            session_key,
        )
        return session

    def session(self, *, session_key: str = DEFAULT_SESSION_KEY) -> GroupManagerSession | None:
        return self._sessions.get(session_key)

    def require_session(self, *, session_key: str = DEFAULT_SESSION_KEY) -> GroupManagerSession:
        session = self._sessions.get(session_key)
        if session is None:
            raise GroupManagerError("No active Group Manager session.")
        return session

    def ensure_session(
        self, workspace: Workspace, *, session_key: str = DEFAULT_SESSION_KEY
    ) -> GroupManagerSession:
        current = self.session(session_key=session_key)
        if current is not None and current.workspace_name == workspace.name:
            return current
        return self.begin_session(workspace, session_key=session_key)

    def leave_session(self, *, session_key: str = DEFAULT_SESSION_KEY) -> None:
        if self._sessions.pop(session_key, None) is not None:
            logger.info("Group Manager session closed (key=%s)", session_key)

    # -- check / working set ----------------------------------------------------------

    def list_backups(self, workspace: Workspace) -> list[BackupSource]:
        return self._checker.list_backups(workspace)

    def run_check(
        self,
        workspace: Workspace,
        backup_name: str,
        descriptor: GroupQueryDescriptor,
        *,
        session_key: str = DEFAULT_SESSION_KEY,
    ) -> WorkingSet:
        session = self.ensure_session(workspace, session_key=session_key)
        working_set = self._checker.run(workspace, backup_name, descriptor)
        session.working_set = working_set
        return working_set

    def working_set(self, *, session_key: str = DEFAULT_SESSION_KEY) -> WorkingSet | None:
        session = self.session(session_key=session_key)
        return session.working_set if session is not None else None

    def require_working_set(self, *, session_key: str = DEFAULT_SESSION_KEY) -> WorkingSet:
        working_set = self.working_set(session_key=session_key)
        if working_set is None:
            raise GroupManagerError("Run Check Group IDs before choosing an action.")
        return working_set

    def clear_working_set(self, *, session_key: str = DEFAULT_SESSION_KEY) -> GroupManagerSession:
        session = self.require_session(session_key=session_key)
        session.working_set = None
        return session

    # -- actions ----------------------------------------------------------------------

    def list_actions(self) -> list[ActionInfo]:
        return [
            ActionInfo(
                id=action.id,
                label=action.label,
                available=action.available,
                description=action.description,
            )
            for action in self._actions.values()
        ]

    def action(self, action_id: str) -> ActionInfo:
        try:
            action = self._actions[action_id]
        except KeyError as exc:
            raise GroupManagerError(f"Unknown action '{action_id}'.") from exc
        return ActionInfo(
            id=action.id,
            label=action.label,
            available=action.available,
            description=action.description,
        )

    def execute_action(
        self,
        workspace: Workspace,
        action_id: str,
        parameters: Mapping[str, Any],
        *,
        session_key: str = DEFAULT_SESSION_KEY,
    ) -> ActionSummary:
        """Execute an action against the current Working Set (no re-search)."""
        working_set = self.require_working_set(session_key=session_key)
        try:
            action = self._actions[action_id]
        except KeyError as exc:
            raise GroupManagerError(f"Unknown action '{action_id}'.") from exc
        if not action.available:
            raise GroupManagerError(f"{action.label} is coming soon.")
        if workspace.name != working_set.workspace:
            raise GroupManagerError("Workspace mismatch for the active Working Set.")
        try:
            action.validate_parameters(parameters, working_set)
            summary = action.execute(working_set, parameters, workspace=workspace)
        except ValueError as exc:
            raise GroupManagerError(str(exc)) from exc
        logger.info(
            "Action '%s' completed for %d matched user(s)",
            summary.action_id,
            summary.user_count,
        )
        return summary
