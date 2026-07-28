"""GroupManagerApplicationService — Catalog → Snapshot → Filter → Matched → Actions → Report."""

from __future__ import annotations

from typing import Any, Mapping, Sequence

from ....core.logging import get_logger
from ....core.workspace import Workspace
from ....integrations.pasarguard.client import PasarGuardClient, PasarGuardError, create_client
from .actions import ActionInfo, GroupAction, PlannedChange, default_actions
from .catalog import GroupCatalog, GroupInfo, load_group_catalog
from .errors import GroupManagerError
from .executor import ProgressHook, execute_planned_changes
from .query import GroupQuery, MatchMode, execute_query
from .reports import ExecutionReport
from .session import GroupManagerSession
from .snapshot import GroupSnapshot, load_group_snapshot
from .working_set import WorkingSet

logger = get_logger("group_manager")

DEFAULT_SESSION_KEY = "default"


class GroupManagerApplicationService:
    """Owns Group Manager lifecycle per Bulk Operations architecture v1.2."""

    def __init__(
        self,
        *,
        actions: Sequence[GroupAction] | None = None,
        client_factory=create_client,
    ) -> None:
        ops = tuple(actions) if actions is not None else default_actions()
        self._actions: dict[str, GroupAction] = {action.id: action for action in ops}
        self._sessions: dict[str, GroupManagerSession] = {}
        self._client_factory = client_factory

    # -- session / catalog / snapshot -------------------------------------------------

    def begin_session(
        self,
        workspace: Workspace,
        *,
        session_key: str = DEFAULT_SESSION_KEY,
        client: PasarGuardClient | None = None,
    ) -> GroupManagerSession:
        """Enter Group Manager: load Group Catalog + create Snapshot."""
        try:
            api = client or self._client_factory(workspace)
            catalog = load_group_catalog(workspace, client=api)
            snapshot = load_group_snapshot(workspace, client=api)
        except PasarGuardError as exc:
            raise GroupManagerError(str(exc)) from exc
        except Exception as exc:  # noqa: BLE001
            raise GroupManagerError(f"Could not load Group Manager session: {exc}") from exc

        session = GroupManagerSession(
            workspace_name=workspace.name,
            catalog=catalog,
            snapshot=snapshot,
        )
        self._sessions[session_key] = session
        logger.info(
            "Group Manager session started for '%s' (%d users, %d groups)",
            workspace.name,
            snapshot.user_count,
            len(catalog),
        )
        return session

    def refresh_snapshot(
        self,
        workspace: Workspace,
        *,
        session_key: str = DEFAULT_SESSION_KEY,
        client: PasarGuardClient | None = None,
    ) -> GroupManagerSession:
        """Full reload: Catalog + Snapshot; clear Query and Working Set."""
        session = self.require_session(session_key=session_key)
        if workspace.name != session.workspace_name:
            raise GroupManagerError("Workspace mismatch for the active Group Manager session.")
        try:
            api = client or self._client_factory(workspace)
            catalog = load_group_catalog(workspace, client=api)
            snapshot = load_group_snapshot(workspace, client=api)
        except PasarGuardError as exc:
            raise GroupManagerError(str(exc)) from exc
        except Exception as exc:  # noqa: BLE001
            raise GroupManagerError(f"Could not refresh Snapshot: {exc}") from exc

        session.catalog = catalog
        session.snapshot = snapshot
        session.query = None
        session.working_set = None
        session.target_rules = ()
        logger.info(
            "Group Manager snapshot refreshed for '%s' (%d users, %d groups)",
            workspace.name,
            snapshot.user_count,
            len(catalog),
        )
        return session

    def session(self, *, session_key: str = DEFAULT_SESSION_KEY) -> GroupManagerSession | None:
        return self._sessions.get(session_key)

    def require_session(self, *, session_key: str = DEFAULT_SESSION_KEY) -> GroupManagerSession:
        session = self._sessions.get(session_key)
        if session is None or session.snapshot is None:
            raise GroupManagerError("No active Group Manager session. Enter Group Manager first.")
        return session

    def ensure_session(
        self,
        workspace: Workspace,
        *,
        session_key: str = DEFAULT_SESSION_KEY,
        client: PasarGuardClient | None = None,
    ) -> GroupManagerSession:
        current = self.session(session_key=session_key)
        if (
            current is not None
            and current.workspace_name == workspace.name
            and current.snapshot is not None
            and current.catalog is not None
        ):
            return current
        return self.begin_session(workspace, session_key=session_key, client=client)

    def leave_session(self, *, session_key: str = DEFAULT_SESSION_KEY) -> None:
        """Destroy Snapshot, Catalog, and all session state."""
        if self._sessions.pop(session_key, None) is not None:
            logger.info("Group Manager session closed (key=%s) — Snapshot destroyed", session_key)

    def snapshot(self, *, session_key: str = DEFAULT_SESSION_KEY) -> GroupSnapshot:
        return self.require_session(session_key=session_key).snapshot  # type: ignore[return-value]

    def catalog(self, *, session_key: str = DEFAULT_SESSION_KEY) -> GroupCatalog:
        session = self.require_session(session_key=session_key)
        if session.catalog is None:
            raise GroupManagerError("Group Catalog is not loaded.")
        return session.catalog

    def available_groups(self, *, session_key: str = DEFAULT_SESSION_KEY) -> tuple[GroupInfo, ...]:
        return self.catalog(session_key=session_key).groups

    # -- query / working set ----------------------------------------------------------

    def run_query(
        self,
        query: GroupQuery,
        *,
        session_key: str = DEFAULT_SESSION_KEY,
    ) -> WorkingSet:
        session = self.require_session(session_key=session_key)
        assert session.snapshot is not None
        working_set = execute_query(session.snapshot, query)
        session.query = query
        session.working_set = working_set
        logger.info(
            "Filter matched %d of %d users (mode=%s include=%s exclude=%s)",
            working_set.matched,
            working_set.total_in_snapshot,
            query.match_mode.value,
            list(query.include_group_ids),
            list(query.exclude_group_ids),
        )
        return working_set

    def working_set(self, *, session_key: str = DEFAULT_SESSION_KEY) -> WorkingSet | None:
        session = self.session(session_key=session_key)
        return session.working_set if session is not None else None

    def require_working_set(self, *, session_key: str = DEFAULT_SESSION_KEY) -> WorkingSet:
        working_set = self.working_set(session_key=session_key)
        if working_set is None:
            raise GroupManagerError("Filter users before choosing an action.")
        return working_set

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

    def preview_action(
        self,
        action_id: str,
        parameters: Mapping[str, Any],
        *,
        session_key: str = DEFAULT_SESSION_KEY,
    ) -> list[PlannedChange]:
        working_set = self.require_working_set(session_key=session_key)
        action = self._get_action(action_id)
        try:
            group_ids = action.validate_parameters(parameters)
        except ValueError as exc:
            raise GroupManagerError(str(exc)) from exc
        return action.plan(working_set.users, group_ids)

    def execute_action(
        self,
        workspace: Workspace,
        action_id: str,
        parameters: Mapping[str, Any],
        *,
        session_key: str = DEFAULT_SESSION_KEY,
        progress: ProgressHook | None = None,
        client: PasarGuardClient | None = None,
    ) -> ExecutionReport:
        session = self.require_session(session_key=session_key)
        working_set = self.require_working_set(session_key=session_key)
        if workspace.name != session.workspace_name:
            raise GroupManagerError("Workspace mismatch for the active Group Manager session.")
        action = self._get_action(action_id)
        if not action.available:
            raise GroupManagerError(f"{action.label} is coming soon.")
        try:
            group_ids = action.validate_parameters(parameters)
        except ValueError as exc:
            raise GroupManagerError(str(exc)) from exc
        planned = action.plan(working_set.users, group_ids)
        query_payload = working_set.query.to_dict() if working_set.query else {}
        report = execute_planned_changes(
            workspace,
            action=action.report_action or action.id,
            query=query_payload,
            planned=planned,
            client=client,
            progress=progress,
        )
        session.last_report_path = str(report.path) if report.path else None
        logger.info(
            "Action '%s' finished: success=%d failed=%d skipped=%d",
            action.id,
            report.summary.success,
            report.summary.failed,
            report.summary.skipped,
        )
        return report

    def _get_action(self, action_id: str) -> GroupAction:
        try:
            return self._actions[action_id]
        except KeyError as exc:
            raise GroupManagerError(f"Unknown action '{action_id}'.") from exc


__all__ = [
    "DEFAULT_SESSION_KEY",
    "GroupManagerApplicationService",
    "GroupQuery",
    "MatchMode",
]
