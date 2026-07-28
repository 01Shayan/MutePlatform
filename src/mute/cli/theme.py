"""Central theme and UI building blocks.

Every screen and every future module reuses these helpers so the application keeps one
consistent, premium identity. Nothing here contains business logic — only presentation.

The module is organized into clearly separated sections (identity, palette, structural
pieces, menus/tables, progress, status). Consumers always access members via the module
(``theme.page()``, ``theme.Icon`` …), so this can later be split into a ``theme/`` package
with a re-exporting ``__init__`` without touching any caller.

Rendering model: the full brand banner is shown only once (at startup, by the splash screen).
Every subsequent screen renders a compact page header — just its title — plus a subtle footer.
"""

from __future__ import annotations

from typing import Iterable, Sequence

from rich.align import Align
from rich.console import Console, Group, RenderableType
from rich.panel import Panel
from rich.progress import (
    BarColumn,
    Progress,
    SpinnerColumn,
    TaskProgressColumn,
    TextColumn,
    TimeElapsedColumn,
)
from rich.prompt import Prompt
from rich.rule import Rule
from rich.table import Table
from rich.text import Text
from rich.theme import Theme

from ..core.constants import APP_NAME, COPYRIGHT, DEVELOPER, FOOTER_TEXT, GITHUB_URL, TAGLINE, VERSION

__all__ = [
    "APP_NAME",
    "TAGLINE",
    "FOOTER_TEXT",
    "DEVELOPER",
    "GITHUB_URL",
    "COPYRIGHT",
    "VERSION",
    "Icon",
    "THEME",
    "console",
    "banner",
    "body_text",
    "footer",
    "section",
    "page_header",
    "page",
    "clear",
    "menu",
    "module_menu",
    "option_menu",
    "history_menu",
    "divider",
    "data_table",
    "summary_panel",
    "info_panel",
    "make_progress",
    "notify_success",
    "notify_error",
    "notify_warning",
    "notify_info",
    "error_panel",
    "pause",
]

# -- identity -------------------------------------------------------------------------
# Canonical values live in ``core.constants``; re-exported here as the UI entry point.


# -- palette --------------------------------------------------------------------------
# Hierarchy: brand=cyan, success=green, warning=yellow, error=red, info=blue,
# headings=bold white, secondary text=dim. Cyan is reserved for brand accents only.

THEME = Theme(
    {
        "brand": "bold cyan",
        "accent": "cyan",
        "heading": "bold white",
        "muted": "dim",
        "key": "bold cyan",
        "value": "white",
        "success": "bold green",
        "warning": "bold yellow",
        "error": "bold red",
        "info": "bold blue",
        "active": "bold green",
        "pending": "yellow",
        "bar.complete": "cyan",
        "bar.finished": "green",
        "bar.pulse": "cyan",
    }
)

console = Console(theme=THEME)


class Icon:
    """Canonical emoji set (the project's emoji standard)."""

    BRAIN = "🧠"
    BACKUP = "📦"
    MIGRATION = "🚚"
    GROUPS = "👥"
    REPORTS = "📊"
    ANALYTICS = "📈"
    MARKETING = "🎯"
    CAMPAIGN = "🎁"
    SETTINGS = "⚙️"
    PROFILE = "👤"
    API = "🌐"
    SEARCH = "🔍"
    EXPORT = "💾"
    IMPORT = "📥"
    RESTORE = "♻️"
    SUCCESS = "✅"
    ERROR = "❌"
    WARNING = "⚠️"
    INFO = "ℹ️"
    PENDING = "⏳"
    PANELS = "🏢"
    WORKSPACES = "💼"
    SHIELD = "🛡"
    FOLDER = "📂"
    DELETE = "🗑️"


# -- structural pieces ----------------------------------------------------------------

def clear() -> None:
    console.clear()


def banner() -> Panel:
    """The full brand banner. Platform-first: name, tagline, version.

    Shown once at startup (on the Main Menu). The current integration is *not* shown here —
    Mute is the platform; PasarGuard is only the current integration and is
    surfaced on the About page and in profile information instead.
    """
    body = Text(justify="center")
    body.append(f"{Icon.BRAIN} {APP_NAME}\n", style="brand")
    body.append("\n")
    body.append(f"{TAGLINE}\n", style="muted")
    body.append("\n")
    body.append(f"v{VERSION}", style="accent")
    return Panel(Align.center(body), border_style="accent", padding=(1, 6))


def body_text(lines: Sequence[str], *, style: str = "value") -> Text:
    """A simple paragraph block: one line per entry."""
    return Text("\n".join(lines), style=style)


def footer() -> Text:
    """A small, subtle footer shown at the bottom of screens."""
    return Align.center(Text(FOOTER_TEXT, style="muted"))


def section(title: str, icon: str | None = None) -> Rule:
    """A titled sub-section separator (muted, understated)."""
    label = f"{icon}  {title}" if icon else title
    return Rule(Text(label, style="heading"), style="muted")


def page_header(title: str, icon: str | None = None) -> Group:
    """A compact page title: bold-white heading over a thin muted rule."""
    label = f"{icon}  {title}" if icon else title
    return Group(Text(label, style="heading"), Rule(style="muted"))


def page(
    title: str,
    *body: RenderableType,
    icon: str | None = None,
    show_footer: bool = True,
) -> None:
    """Render a page: clear, compact header, body, and (optionally) the subtle footer.

    Body renderables are positional arguments after ``title``. Pass ``icon`` only as a
    keyword argument so Rich components are never mistaken for the icon slot.
    """
    console.clear()
    console.print(page_header(title, icon))
    console.print()
    for item in body:
        console.print(item)
    if show_footer:
        console.print()
        console.print(footer())


# -- menus & tables -------------------------------------------------------------------

def menu(title: str, items: Sequence[tuple], subtitle: str | None = None) -> Panel:
    """Render a menu panel.

    ``items`` are ``(key, icon, label)`` or ``(key, icon, label, description)`` tuples.
    When a description is present it is shown on a dim second line.
    """
    grid = Table.grid(padding=(0, 2))
    grid.add_column(justify="right", style="key", no_wrap=True)
    grid.add_column()

    for index, item in enumerate(items):
        key, icon, label = item[0], item[1], item[2]
        description = item[3] if len(item) > 3 else ""
        prefix = f"{icon}  " if icon else ""
        grid.add_row(f"[{key}]", Text(f"{prefix}{label}", style="heading"))
        if description:
            grid.add_row("", Text(description, style="muted"))
            if index != len(items) - 1:
                grid.add_row("", "")

    return Panel(
        grid,
        title=title,
        title_align="left",
        subtitle=subtitle,
        subtitle_align="right",
        border_style="muted",
        padding=(1, 2),
    )


def module_menu(items: Sequence[tuple]) -> Table:
    """A clean, unboxed list of ``(key, icon, label)`` entries for the Main Menu."""
    grid = Table.grid(padding=(0, 2))
    grid.add_column(justify="right", style="accent", no_wrap=True)
    grid.add_column(no_wrap=True)
    for key, icon, label in items:
        prefix = f"{icon}  " if icon else ""
        grid.add_row(key, Text(f"{prefix}{label}", style="heading"))
    return grid


def option_menu(items: Sequence[tuple]) -> Table:
    """A numbered, icon-free menu: ``(key, label)`` or ``(key, label, subtitle)`` tuples.

    Rendered as ``key. label`` with an optional dim subtitle line beneath (used to show a
    workspace's integration under its name).
    """
    grid = Table.grid(padding=(0, 1))
    grid.add_column(justify="right", style="accent", no_wrap=True)
    grid.add_column()
    for item in items:
        key, label = item[0], item[1]
        subtitle = item[2] if len(item) > 2 else None
        grid.add_row(f"{key}.", Text(label, style="heading"))
        if subtitle:
            grid.add_row("", Text(subtitle, style="muted"))
    return grid


def history_menu(items: Sequence[tuple]) -> Table:
    """Numbered list with multi-line muted details: ``(key, headline, *detail_lines)``."""
    grid = Table.grid(padding=(0, 1))
    grid.add_column(justify="right", style="accent", no_wrap=True)
    grid.add_column()
    for item in items:
        key, headline, *details = item
        grid.add_row(f"{key}.", Text(headline, style="heading"))
        for line in details:
            grid.add_row("", Text(line, style="muted"))
    return grid


def divider() -> Rule:
    """A plain horizontal separator."""
    return Rule(style="muted")


def data_table(columns: Sequence[str], *, title: str | None = None) -> Table:
    """A consistently styled table ready for ``add_row`` calls."""
    table = Table(
        title=title,
        title_style="heading",
        header_style="heading",
        border_style="muted",
        expand=False,
    )
    for column in columns:
        table.add_column(column)
    return table


def summary_panel(title: str, rows: Iterable[tuple[str, str]], *, style: str = "success") -> Panel:
    """A key/value summary block, e.g. the result of a completed task."""
    grid = Table.grid(padding=(0, 2))
    grid.add_column(justify="right", style="key", no_wrap=True)
    grid.add_column(style="value")
    for label, value in rows:
        grid.add_row(label, value)
    return Panel(grid, title=title, title_align="left", border_style=style, padding=(1, 2))


def info_panel(rows: Iterable[tuple[str, str]]) -> Panel:
    """Standard aligned information block for confirmations and reviews (no panel title)."""
    grid = Table.grid(padding=(0, 2))
    grid.add_column(justify="right", style="key", no_wrap=True)
    grid.add_column(style="value")
    for label, value in rows:
        grid.add_row(label, value)
    return Panel(grid, border_style="info", padding=(1, 2))


# -- progress -------------------------------------------------------------------------

def make_progress() -> Progress:
    """A standard progress bar for long-running tasks."""
    return Progress(
        SpinnerColumn(style="accent"),
        TextColumn("[muted]{task.description}"),
        BarColumn(bar_width=None),
        TaskProgressColumn(),
        TimeElapsedColumn(),
        console=console,
    )


# -- status messages ------------------------------------------------------------------

def _badge(icon: str, text: str, style: str) -> Text:
    return Text.assemble((f"{icon}  ", style), (text, style))


def notify_success(message: str) -> None:
    console.print(_badge(Icon.SUCCESS, message, "success"))


def notify_error(message: str) -> None:
    console.print(_badge(Icon.ERROR, message, "error"))


def notify_warning(message: str) -> None:
    console.print(_badge(Icon.WARNING, message, "warning"))


def notify_info(message: str) -> None:
    console.print(_badge(Icon.INFO, message, "info"))


def error_panel(title: str, detail: str) -> Panel:
    """A human-friendly error panel (never a raw traceback)."""
    body = Text()
    body.append(f"{Icon.ERROR}  {title}\n\n", style="error")
    body.append(detail, style="value")
    return Panel(body, border_style="error", padding=(1, 2))


# -- interaction ----------------------------------------------------------------------

def pause(message: str = "Press Enter to continue") -> None:
    """Wait for the user before returning to the previous screen."""
    Prompt.ask(f"\n[muted]{message}[/muted]", default="", show_default=False)
