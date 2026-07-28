"""Workspace Dashboard — the tools and management for the selected workspace.

All operations belong to the workspace. Reached after opening a workspace.
"""

from __future__ import annotations

from rich.prompt import Confirm, Prompt

from ...core.context import AppContext
from ...core.integrations import integration_name
from ...core.workspace import Workspace, WorkspaceStore
from ...services.workspace import ConnectionStatus, WorkspaceApplicationService
from ...ui.copy import (
    BTN_BACK,
    MENU_BACKUP,
    MENU_BULK_OPS,
    MENU_DELETE_WORKSPACE,
    MENU_EDIT_WORKSPACE,
    MENU_MIGRATION,
)
from .. import theme
from ..theme import Icon, console
from . import backup, bulk_operations, placeholder, wsforms

_TOOLS = [
    ("1", MENU_BACKUP),
    ("2", MENU_BULK_OPS),
    ("3", MENU_MIGRATION),
]
_MANAGE = [
    ("4", MENU_EDIT_WORKSPACE),
    ("5", MENU_DELETE_WORKSPACE),
    ("0", BTN_BACK),
]

_INTROS = {
    MENU_MIGRATION: [
        "Import users into a panel.",
        "Create users safely from a backup or SQL source.",
    ],
}


def run(store: WorkspaceStore, app: AppContext, workspace: Workspace) -> None:
    status = _verify_and_status_label(workspace)
    while True:
        theme.page(
            workspace.name,
            theme.info_panel(
                [
                    ("Panel", integration_name(workspace.integration)),
                    ("Status", status),
                ]
            ),
            "",
            theme.option_menu(_TOOLS),
            theme.divider(),
            theme.option_menu(_MANAGE),
        )
        choice = Prompt.ask(
            "\nSelect an option",
            choices=[k for k, _ in _TOOLS + _MANAGE],
            default="0",
            show_choices=False,
        )
        if choice == "0":
            return
        if choice == "1":
            backup.run(workspace)
            status = WorkspaceApplicationService.status_label(
                WorkspaceApplicationService.connection_status(workspace)
            )
        elif choice == "2":
            bulk_operations.run(workspace)
        elif choice == "3":
            placeholder.coming_soon(Icon.MIGRATION, MENU_MIGRATION, _INTROS[MENU_MIGRATION])
        elif choice == "4":
            workspace = _edit_workspace(store, app, workspace)
            status = _verify_and_status_label(workspace)
        elif choice == "5":
            if _delete_workspace(store, app, workspace):
                return


def _verify_and_status_label(workspace: Workspace) -> str:
    """Probe the panel, persist the shared cache, then return the canonical label."""
    try:
        with console.status("[muted]Checking connection…[/muted]", spinner="dots"):
            WorkspaceApplicationService.connection_is_available(workspace)
    except Exception:  # noqa: BLE001 — UI feedback must never break the dashboard
        WorkspaceApplicationService.record_connection_status(workspace, ConnectionStatus.OFFLINE)
    return WorkspaceApplicationService.status_label(
        WorkspaceApplicationService.connection_status(workspace)
    )


# -- Edit ---------------------------------------------------------------------------------

def _edit_workspace(store: WorkspaceStore, app: AppContext, workspace: Workspace) -> Workspace:
    theme.page(
        "Edit Workspace",
        theme.body_text([f"Editing '{workspace.name}'.", "Leave a field unchanged to keep it."]),
    )

    service = WorkspaceApplicationService(store)
    integration = wsforms.choose_integration(
        service, title="Edit Workspace", current_key=workspace.integration
    )
    if integration is None:
        integration_key = workspace.integration
    else:
        integration_key = integration.key
        if integration_key != workspace.integration and not service.integration_is_available(integration):
            theme.notify_info(f"{integration.name} integration is coming in a future version.")
            theme.pause()
            integration_key = workspace.integration

    if integration_key != workspace.integration:
        if not Confirm.ask(
            f"\nChange integration from {integration_name(workspace.integration)} to "
            f"{integration_name(integration_key)}? Existing data stays in place.",
            default=False,
        ):
            integration_key = workspace.integration

    new_name = wsforms.prompt_name(service, current=workspace.name)
    if new_name is None:
        return workspace

    fields = wsforms.prompt_connection(source=workspace)
    if not Confirm.ask("\nSave changes?", default=True):
        theme.notify_info("Cancelled. No changes were made.")
        theme.pause()
        return workspace

    updated = service.update(
        workspace, name=new_name, integration=integration_key, connection=fields
    )
    if updated is None:
        theme.notify_error(f"Could not rename to '{new_name}'.")
        theme.pause()
        return workspace
    app.open_workspace(updated)
    theme.notify_success("Workspace updated.")
    theme.pause()
    return updated


# -- Delete -------------------------------------------------------------------------------

def _delete_workspace(store: WorkspaceStore, app: AppContext, workspace: Workspace) -> bool:
    theme.page(
        "Delete Workspace",
        theme.summary_panel(
            "Workspace",
            [("Workspace", workspace.name), ("Warning", "This action cannot be undone.")],
            style="error",
        ),
        "",
        theme.option_menu([("1", "Yes"), ("0", "No")]),
    )
    choice = Prompt.ask(
        "\nSelect an option", choices=["1", "0"], default="0", show_choices=False
    )
    if choice != "1":
        return False

    WorkspaceApplicationService(store).delete(workspace)
    if app.workspace is not None and app.workspace.name == workspace.name:
        app.workspace = None
        app.user = None
    theme.notify_success(f"Workspace '{workspace.name}' deleted.")
    theme.pause()
    return True
