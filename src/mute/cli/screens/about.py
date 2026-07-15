"""ℹ️ About screen — minimal platform information."""

from __future__ import annotations

from .. import theme


def show() -> None:
    info = theme.summary_panel(
        "Platform",
        [
            ("Platform", theme.APP_NAME),
            ("Version", f"v{theme.VERSION}"),
            ("Developer", theme.DEVELOPER),
            ("GitHub", theme.GITHUB_URL),
        ],
        style="info",
    )
    theme.page("About", info)
    theme.pause()
