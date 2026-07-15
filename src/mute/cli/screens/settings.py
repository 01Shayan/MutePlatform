"""⚙️ Settings — placeholders only for v0.1."""

from __future__ import annotations

from .. import theme


_SECTIONS = ("Appearance", "Language", "Logging", "Backup", "Advanced")


def show() -> None:
    table = theme.data_table(["Setting", "Status"])
    for name in _SECTIONS:
        table.add_row(name, "[muted]Coming soon[/muted]")

    theme.page(
        "Settings",
        theme.body_text(["Application preferences.", "Manage interface and future configuration."]),
        "",
        table,
    )
    theme.pause()
