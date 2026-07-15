"""Application shell: startup and the Home screen.

The platform is workspace-centric. Navigation hierarchy::

    Home → Workspaces → (open) → Workspace Dashboard → Backup / Group Checker / Migration

The app always starts at Home. No module runs on its own; every action returns here when
finished. Business logic lives in modules — this file only routes.

The full brand banner appears once (on the first Home render, at startup). Every other screen
renders only its page content.
"""

from __future__ import annotations

from rich.prompt import Prompt

from ..core.config import ensure_settings, is_first_run
from ..core.context import AppContext
from ..core.workspace import WorkspaceStore
from ..services.workspace import WorkspaceApplicationService
from . import theme
from .screens import about, settings, splash, wizard, workspaces
from .theme import Icon, console

# (key, label)
_HOME_ITEMS = [
    ("1", "My Workspaces"),
    ("2", "Settings"),
    ("3", "About"),
    ("0", "Exit"),
]


class Application:
    """Owns shared state (workspace store, app context) and drives the Home loop."""

    def __init__(self) -> None:
        ensure_settings()
        self.store = WorkspaceStore()
        self.workspaces = WorkspaceApplicationService(self.store)
        active = self.workspaces.initialize()
        self.context = AppContext()
        if active is not None:
            self.context.open_workspace(active)  # also routes logging into the workspace
        self._banner_shown = False

    # -- main loop --------------------------------------------------------------------

    def run(self) -> None:
        while True:
            self._render_home()
            choice = Prompt.ask(
                "\nSelect an option",
                choices=[item[0] for item in _HOME_ITEMS],
                default="0",
                show_choices=False,
            )
            if choice == "0":
                self._goodbye()
                return
            self._dispatch(choice)

    def _dispatch(self, choice: str) -> None:
        if choice == "1":
            workspaces.run(self.store, self.context)
        elif choice == "2":
            settings.show()
        elif choice == "3":
            about.show()

    # -- rendering --------------------------------------------------------------------

    def _render_home(self) -> None:
        console.clear()
        if not self._banner_shown:
            console.print(theme.banner())
            console.print()
            self._banner_shown = True
        console.print(theme.option_menu(_HOME_ITEMS))
        console.print()
        console.print(theme.footer())

    def _goodbye(self) -> None:
        theme.page(
            "Goodbye",
            theme.body_text(["Thank you for using Mute Platform."]),
            icon=Icon.INFO,
        )


def run() -> int:
    try:
        if is_first_run():
            wizard.run()
        splash.show()
        Application().run()
    except (KeyboardInterrupt, EOFError):
        console.print()
        theme.notify_info("Interrupted. Goodbye.")
    return 0
