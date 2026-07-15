"""Lightweight application context.

Holds the currently selected workspace and user, so screens read one shared context instead of
querying storage everywhere. Intentionally minimal.
"""

from __future__ import annotations

from dataclasses import dataclass

from .integrations import integration_name
from .logging import use_workspace
from .workspace import Workspace


@dataclass
class AppContext:
    workspace: Workspace | None = None
    user: str | None = None

    @property
    def workspace_name(self) -> str:
        return self.workspace.name if self.workspace is not None else "—"

    @property
    def integration(self) -> str:
        if self.workspace is None:
            return "—"
        return integration_name(self.workspace.integration)

    def open_workspace(self, workspace: Workspace) -> None:
        self.workspace = workspace
        self.user = workspace.username or None
        # Every workspace owns its logs — route all channels into this workspace.
        use_workspace(workspace.logs_dir)
