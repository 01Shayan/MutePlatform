"""Generic multi-select selector — foundation for Group / Status / Workspace selectors."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Sequence


@dataclass(frozen=True)
class SelectableItem:
    id: int | str
    label: str


@dataclass
class SelectionState:
    """Mutable selection state for a selector session."""

    available: tuple[SelectableItem, ...]
    selected: set[int | str] = field(default_factory=set)
    multi_select: bool = True

    def toggle(self, item_id: int | str) -> None:
        if item_id not in {item.id for item in self.available}:
            raise ValueError(f"Unknown option: {item_id}")
        if item_id in self.selected:
            self.selected.discard(item_id)
        elif self.multi_select:
            self.selected.add(item_id)
        else:
            self.selected = {item_id}

    def selected_ids(self) -> tuple:
        order = {item.id: index for index, item in enumerate(self.available)}
        return tuple(sorted(self.selected, key=lambda value: order.get(value, 0)))

    def is_selected(self, item_id: int | str) -> bool:
        return item_id in self.selected


def format_checklist(state: SelectionState) -> list[str]:
    lines: list[str] = []
    for item in state.available:
        mark = "☑" if state.is_selected(item.id) else "☐"
        lines.append(f"{mark} {item.label}")
    return lines


def format_selected_summary(state: SelectionState, *, empty: str = "—") -> list[str]:
    from ..copy import SELECTOR_SELECTED

    ids = state.selected_ids()
    count = len(ids)
    if count == 0:
        return [SELECTOR_SELECTED, "0 Groups", empty]
    noun = "Group" if count == 1 else "Groups"
    return [
        SELECTOR_SELECTED,
        f"{count} {noun}",
        ", ".join(str(value) for value in ids),
    ]


def validate_selection(
    state: SelectionState,
    *,
    allow_empty: bool = False,
) -> str | None:
    """Return an error message, or None if valid."""
    available_ids = {item.id for item in state.available}
    unknown = [value for value in state.selected if value not in available_ids]
    if unknown:
        return f"Unknown selection: {', '.join(str(value) for value in unknown)}"
    if not allow_empty and not state.selected:
        return "empty"
    return None
