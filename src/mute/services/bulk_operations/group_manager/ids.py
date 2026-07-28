"""Shared helpers for Group Manager."""

from __future__ import annotations


def parse_group_ids(raw: str) -> tuple[int, ...]:
    """Parse a comma/space-separated list of group IDs."""
    parts = (raw or "").replace(",", " ").split()
    if not parts:
        raise ValueError("Enter at least one numeric group ID (e.g. 1, 3).")
    ids: list[int] = []
    for part in parts:
        try:
            ids.append(int(part))
        except ValueError as exc:
            raise ValueError(f"Invalid group ID '{part}'. Use numbers only (e.g. 1, 3).") from exc
    seen: set[int] = set()
    unique: list[int] = []
    for value in ids:
        if value not in seen:
            seen.add(value)
            unique.append(value)
    return tuple(unique)


def format_group_ids(ids: tuple[int, ...]) -> str:
    return ", ".join(str(value) for value in ids) if ids else "—"
