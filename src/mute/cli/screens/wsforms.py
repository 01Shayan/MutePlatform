"""Shared workspace form helpers (used by Add and Edit).

Kept separate so both the create wizard and the edit screen reuse the same prompts without a
circular import between the workspaces list and the dashboard.
"""

from __future__ import annotations

from rich.prompt import Confirm, Prompt

from ...core.integrations import Integration
from ...core.workspace import Workspace
from ...services.workspace import WorkspaceApplicationService
from .. import theme
from ..theme import Icon, console


def choose_integration(
    service: WorkspaceApplicationService, *, title: str = "Add Workspace", current_key: str | None = None
) -> Integration | None:
    """Step 1 — pick an integration. Returns None if cancelled."""
    integrations = service.integrations()
    items = []
    for index, integration in enumerate(integrations, start=1):
        suffix = "" if integration.available else "  (coming soon)"
        items.append((str(index), f"{integration.name}{suffix}"))
    items.append(("0", "Cancel"))

    step = "Step 1 of 3" if title == "Add Workspace" else "Select integration"
    theme.page(
        title,
        theme.body_text([step, "Select the integration for this workspace."]),
        "",
        theme.option_menu(items),
    )
    choice = Prompt.ask(
        "\nSelect an integration",
        choices=[item[0] for item in items],
        default="0",
        show_choices=False,
    )
    if choice == "0":
        return None
    return integrations[int(choice) - 1]


def prompt_name(service: WorkspaceApplicationService, *, current: str | None = None) -> str | None:
    console.print()
    console.print(theme.section("Workspace Name", Icon.WORKSPACES))
    name = Prompt.ask("Workspace name", default=current).strip()
    if not name:
        theme.notify_warning("Name cannot be empty. Cancelled.")
        theme.pause()
        return None
    if not service.name_is_available(name, current=current):
        theme.notify_error(f"A workspace named '{name}' already exists.")
        theme.pause()
        return None
    return name


def prompt_connection(source: Workspace | None = None) -> dict:
    console.print()
    console.print(theme.section("Connection", Icon.API))

    base_url = Prompt.ask("Base URL", default=source.base_url if source else None)
    console.print("[muted]  1 = username/password   2 = token[/muted]")
    default_method = "2" if (source and source.token and not source.has_credentials) else "1"
    method = Prompt.ask(
        "Authentication method", choices=["1", "2"], default=default_method, show_choices=False
    )

    username = password = token = None
    if method == "1":
        username = Prompt.ask("Username", default=source.username if source else None)
        note = " (leave blank to keep current)" if source and source.password else ""
        password = Prompt.ask(f"Password{note}", password=True, default="") or None
        if source and not password:
            password = source.password
    else:
        token = Prompt.ask("Bearer token", default=source.token if source else None) or None

    verify_ssl = Confirm.ask(
        "Verify TLS certificate?", default=source.verify_ssl if source else True
    )
    return {
        "base_url": base_url,
        "username": username,
        "password": password,
        "token": token,
        "verify_ssl": verify_ssl,
    }
