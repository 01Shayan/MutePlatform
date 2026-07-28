"""Layout primitives shared by CLI and Telegram text rendering."""

from __future__ import annotations

from typing import Sequence

DIVIDER = "────────────────────"


def format_screen(
    *,
    title: str,
    summary: Sequence[str] | None = None,
    content: Sequence[str] | None = None,
    actions: Sequence[str] | None = None,
    navigation: Sequence[str] | None = None,
) -> list[str]:
    """Standard screen layout: Title → Summary → Content → Actions → Navigation."""
    lines: list[str] = [title]
    if summary:
        if lines[-1]:
            lines.append("")
        lines.extend(summary)
    if content is not None:
        lines.append(DIVIDER)
        lines.extend(content)
    if actions:
        lines.append(DIVIDER)
        lines.extend(actions)
    if navigation:
        lines.append(DIVIDER)
        lines.extend(navigation)
    return lines
