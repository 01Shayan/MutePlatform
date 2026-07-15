"""Workspace lifecycle operations shared by all interfaces."""

from __future__ import annotations

from dataclasses import dataclass

from ...core.integrations import Integration, integration_name, list_integrations
from ...core.workspace import Workspace, WorkspaceStore, bootstrap
from ...integrations.pasarguard.client import create_client


@dataclass(frozen=True)
class WorkspaceNavigationItem:
    """Read-only workspace information safe for interface navigation."""

    name: str
    panel: str


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
        return [
            WorkspaceNavigationItem(workspace.name, integration_name(workspace.integration))
            for workspace in self.list()
        ]

    def navigation_item(self, name: str) -> WorkspaceNavigationItem | None:
        workspace = next((item for item in self.list() if item.name == name), None)
        if workspace is None:
            return None
        return WorkspaceNavigationItem(workspace.name, integration_name(workspace.integration))

    def workspace(self, name: str) -> Workspace | None:
        """Return a workspace only for passing to another application service."""
        return next((item for item in self.list() if item.name == name), None)

    def activate(self, workspace: Workspace) -> bool:
        return self.store.set_active(workspace.name)

    def name_is_available(self, name: str, *, current: str | None = None) -> bool:
        return name == current or not self.store.exists(name)

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
        """Probe a workspace without exposing integration details to an interface."""
        try:
            create_client(workspace, timeout=timeout).test_connection()
            return True
        except Exception:  # A dashboard status probe is deliberately best-effort.
            return False
