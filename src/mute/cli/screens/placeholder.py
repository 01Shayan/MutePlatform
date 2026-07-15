"""Placeholder screen for features that are planned but not yet implemented.

Each planned module still introduces itself on its own page, then shows a "Coming soon" note.
"""

from __future__ import annotations

from typing import Sequence

from .. import theme


def coming_soon(icon: str, title: str, description: Sequence[str]) -> None:
    theme.page(
        title,
        theme.body_text(list(description)),
        "",
        theme.summary_panel(
            "Status",
            [("Module", title), ("State", "Coming soon")],
            style="info",
        ),
        icon=icon,
    )
    theme.pause()
