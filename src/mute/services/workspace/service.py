"""Workspace lifecycle operations shared by all interfaces."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path

from ...core.integrations import Integration, integration_name, list_integrations
from ...core.jsonio import write_json_atomic
from ...core.workspace import (
    InvalidWorkspaceName,
    Workspace,
    WorkspaceStore,
    bootstrap,
    validate_workspace_name,
)
from ...integrations.pasarguard.client import create_client

_STATUS_FILENAME = "connection_status.json"


class ConnectionStatus(str, Enum):
    """Cached panel reachability — never probed on every dashboard open."""

    CONNECTED = "connected"
    OFFLINE = "offline"
    UNKNOWN = "unknown"


_STATUS_LABELS = {
    ConnectionStatus.CONNECTED: "🟢 Connected",
    ConnectionStatus.OFFLINE: "🔴 Offline",
    ConnectionStatus.UNKNOWN: "⚪ Unknown",
}


@dataclass(frozen=True)
class WorkspaceNavigationItem:
    """Read-only workspace information safe for interface navigation."""

    name: str
    panel: str
    status: ConnectionStatus = ConnectionStatus.UNKNOWN


class WorkspaceOperationError(Exception):
    """A safe, interface-ready explanation of a workspace operation failure."""


class WorkspaceApplicationService:
    def __init__(self, store: WorkspaceStore) -> None:
        self.store = store

    def create(self, *, name: str, integration: str, connection: dict) -> Workspace:
        return self.store.create(Workspace(name=name, integration=integration, **connection), make_active=True)

    def initialize(self) -> Workspace | None:
        """Run the one-time workspace migration/bootstrap and return the active workspace."""
        bootstrap(self.store)
        return self.store.get_active()

    def list(self) -> list[Workspace]:
        return self.store.list()

    @classmethod
    def for_navigation(cls) -> "WorkspaceApplicationService":
        """Create the read-only workspace gateway used by an interface."""
        return cls(WorkspaceStore())

    def navigation_items(self) -> list[WorkspaceNavigationItem]:
        return [self._to_navigation_item(workspace) for workspace in self.list()]

    def navigation_item(self, name: str) -> WorkspaceNavigationItem | None:
        workspace = self.workspace(name)
        if workspace is None:
            return None
        return self._to_navigation_item(workspace)

    def workspace(self, name: str) -> Workspace | None:
        """Return a workspace only for passing to another application service."""
        return self.store.get(name)

    def activate(self, workspace: Workspace) -> bool:
        return self.store.set_active(workspace.name)

    def name_is_available(self, name: str, *, current: str | None = None) -> bool:
        if name == current:
            return True
        if self.store.exists(name):
            return False
        return self.store.dir_is_free(name, current=current)

    def validate_name(self, name: str, *, current: str | None = None) -> str:
        """Validate and normalize a workspace name for interfaces."""
        try:
            cleaned = validate_workspace_name(name)
        except InvalidWorkspaceName as exc:
            raise WorkspaceOperationError(str(exc)) from exc
        if not self.name_is_available(cleaned, current=current):
            raise WorkspaceOperationError(f"A workspace named '{cleaned}' already exists.")
        return cleaned

    @staticmethod
    def integrations() -> list[Integration]:
        return list(list_integrations())

    @staticmethod
    def integration_is_available(integration: Integration) -> bool:
        return integration.available

    def update(self, workspace: Workspace, *, name: str, integration: str, connection: dict) -> Workspace | None:
        if name != workspace.name and not self.store.rename(workspace.name, name):
            return None
        updated = Workspace(name=name, integration=integration, created_at=workspace.created_at, **connection)
        self.store.save(updated)
        self.store.set_active(updated.name)
        return updated

    def delete(self, workspace: Workspace) -> bool:
        return self.store.delete(workspace.name)

    @staticmethod
    def connection_is_available(workspace: Workspace, *, timeout: float = 6) -> bool:
        """Probe a workspace and persist the outcome for later status display."""
        ok = WorkspaceApplicationService.probe_connection(workspace, timeout=timeout)
        WorkspaceApplicationService.record_connection_status(
            workspace, ConnectionStatus.CONNECTED if ok else ConnectionStatus.OFFLINE
        )
        return ok

    @staticmethod
    def probe_connection(workspace: Workspace, *, timeout: float = 6) -> bool:
        """Probe a workspace without persisting status (used during wizards)."""
        try:
            create_client(workspace, timeout=timeout).test_connection()
            return True
        except Exception:  # Best-effort connectivity check.
            return False

    @staticmethod
    def status_label(status: ConnectionStatus) -> str:
        """Canonical status text shared by every interface."""
        return _STATUS_LABELS.get(status, _STATUS_LABELS[ConnectionStatus.UNKNOWN])

    @staticmethod
    def connection_status(workspace: Workspace) -> ConnectionStatus:
        """Return the last known connection status without contacting the panel."""
        path = WorkspaceApplicationService._status_path(workspace)
        if not path.exists():
            return ConnectionStatus.UNKNOWN
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
            return ConnectionStatus(str(raw.get("status", "unknown")))
        except (json.JSONDecodeError, OSError, ValueError):
            return ConnectionStatus.UNKNOWN

    @staticmethod
    def record_connection_status(workspace: Workspace, status: ConnectionStatus) -> None:
        """Persist a connection probe outcome under the workspace cache folder."""
        workspace.ensure_dirs()
        write_json_atomic(
            WorkspaceApplicationService._status_path(workspace),
            {"status": status.value, "checked_at": datetime.now().isoformat(timespec="seconds")},
        )

    def clear_all_tokens(self) -> int:
        """Remove saved bearer tokens from every workspace. Passwords and other fields stay."""
        cleared = 0
        for workspace in self.list():
            if not workspace.token:
                continue
            workspace.token = None
            self.store.save(workspace)
            cleared += 1
        return cleared

    def _to_navigation_item(self, workspace: Workspace) -> WorkspaceNavigationItem:
        return WorkspaceNavigationItem(
            workspace.name,
            integration_name(workspace.integration),
            WorkspaceApplicationService.connection_status(workspace),
        )

    @staticmethod
    def _status_path(workspace: Workspace) -> Path:
        return workspace.cache_dir / _STATUS_FILENAME
