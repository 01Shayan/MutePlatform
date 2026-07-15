"""Human-friendly relative time formatting.

Pure logic (no UI), so it stays testable and reusable.
"""

from __future__ import annotations

from datetime import datetime


def _plural(value: int, unit: str) -> str:
    return f"{value} {unit}{'' if value == 1 else 's'} ago"


def relative_time(moment: datetime, *, now: datetime | None = None) -> str:
    """Return a friendly relative label, e.g. ``"2 hours ago"``, ``"Yesterday"``."""
    now = now or datetime.now()
    seconds = (now - moment).total_seconds()
    if seconds < 0:
        seconds = 0

    if seconds < 60:
        return _plural(max(1, int(seconds)), "second")
    if seconds < 3600:
        return _plural(int(seconds // 60), "minute")
    if seconds < 86400:
        return _plural(int(seconds // 3600), "hour")

    days = (now.date() - moment.date()).days
    if days <= 1:
        return "Yesterday"
    if days < 7:
        return f"{days} days ago"
    return moment.strftime("%Y-%m-%d")
