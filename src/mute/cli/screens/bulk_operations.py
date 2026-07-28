"""Bulk Operations — top-level home for bulk modification modules.

v0.3.0 exposes Group Manager only. Presentation follows the Design System.
"""

from __future__ import annotations

from rich.prompt import Prompt

from ...core.workspace import Workspace
from ...ui.copy import BTN_BACK, BULK_OPS_INTRO, MENU_GROUP_MANAGER, TITLE_BULK_OPS
from .. import theme
from . import group_manager

_MODULES = [
    ("1", MENU_GROUP_MANAGER),
    ("0", BTN_BACK),
]


def run(workspace: Workspace) -> None:
    while True:
        theme.page(
            TITLE_BULK_OPS,
            theme.body_text(BULK_OPS_INTRO.splitlines()),
            "",
            theme.option_menu(_MODULES),
        )
        choice = Prompt.ask(
            "\nSelect an option",
            choices=[item[0] for item in _MODULES],
            default="0",
            show_choices=False,
        )
        if choice == "0":
            return
        if choice == "1":
            group_manager.run(workspace)
