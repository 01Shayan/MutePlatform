"""My Workspaces — list, open, and create workspaces.

The user only ever works with workspaces (never "profiles" or "panels"). Opening a workspace
enters its dashboard.
"""

from __future__ import annotations

from rich.prompt import Confirm, Prompt

from ...core.context import AppContext
from ...core.integrations import integration_name
from ...core.workspace import Workspace, WorkspaceStore
from ...services.workspace import WorkspaceApplicationService
from ...ui.copy import BTN_BACK, MENU_ADD_WORKSPACE, MENU_MY_WORKSPACES
from .. import theme
from . import dashboard, wsforms


def run(store: WorkspaceStore, app: AppContext) -> None:
    service = WorkspaceApplicationService(store)
    while True:
        workspaces = service.list()
        add_key = str(len(workspaces) + 1)

        ws_items = [
            (str(i), ws.name, integration_name(ws.integration))
            for i, ws in enumerate(workspaces, start=1)
        ]
        action_items = [(add_key, MENU_ADD_WORKSPACE), ("0", BTN_BACK)]

        body = []
        if ws_items:
            body.append(theme.option_menu(ws_items))
            body.append(theme.divider())
        else:
            body.append(theme.body_text(["No workspaces yet. Choose Add Workspace to begin."]))
            body.append("")
        body.append(theme.option_menu(action_items))
        theme.page(MENU_MY_WORKSPACES, *body)

        choices = [str(i) for i in range(1, len(workspaces) + 1)] + [add_key, "0"]
        choice = Prompt.ask(
            "\nSelect an option", choices=choices, default="0", show_choices=False
        )

        if choice == "0":
            return
        if choice == add_key:
            _add_workspace(service, app)
            continue
        workspace = workspaces[int(choice) - 1]
        app.open_workspace(workspace)
        service.activate(workspace)
        dashboard.run(store, app, workspace)


# -- Add Workspace wizard -----------------------------------------------------------------

def _add_workspace(service: WorkspaceApplicationService, app: AppContext) -> None:
    integration = wsforms.choose_integration(service)
    if integration is None:
        return
    if not service.integration_is_available(integration):
        theme.notify_info(f"{integration.name} integration is coming in a future version.")
        theme.pause()
        return

    name = wsforms.prompt_name(service)
    if name is None:
        return

    fields = wsforms.prompt_connection()
    if not Confirm.ask("\nCreate this workspace?", default=True):
        theme.notify_info("Cancelled. No workspace was created.")
        theme.pause()
        return

    workspace = service.create(
        name=name, integration=integration.key, connection=fields
    )
    app.open_workspace(workspace)
    theme.notify_success(f"Workspace '{name}' created.")
    theme.pause()
