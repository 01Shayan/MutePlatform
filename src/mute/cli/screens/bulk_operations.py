"""Bulk Operations — top-level home for bulk modification modules.

v0.3.0 exposes Group Manager only.
"""

from __future__ import annotations

from rich.prompt import Prompt

from ...core.workspace import Workspace
from .. import theme
from ..theme import Icon
from . import group_manager

_MODULES = [
    ("1", "Group Manager"),
    ("0", "Back"),
]


def run(workspace: Workspace) -> None:
    while True:
        theme.page(
            "Bulk Operations",
            theme.body_text(
                [
                    "Home for bulk modification workflows.",
                    "Each manager owns one domain of panel changes.",
                ]
            ),
            "",
            theme.option_menu(_MODULES),
            icon=Icon.GROUPS,
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
