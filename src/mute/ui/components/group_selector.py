"""Shared Group Selector — select one or more Groups from a known catalogue.

CLI and Telegram must use this component for every Group selection screen.
No business logic lives here.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from ..copy import (
    BTN_BACK,
    DIVIDER,
    MSG_SELECT_AT_LEAST_ONE_GROUP,
    SELECTOR_NO_GROUPS,
    SELECTOR_SELECTED,
    SELECTOR_SUBTITLE_ADD,
    SELECTOR_SUBTITLE_CURRENT,
    SELECTOR_SUBTITLE_REMOVE,
    SELECTOR_SUBTITLE_REPLACE,
    SELECTOR_SUBTITLE_SELECT,
    TARGET_CONTINUE,
)
from .selector import (
    SelectableItem,
    SelectionState,
    format_checklist,
    validate_selection,
)

# Public subtitle aliases (Design System)
SUBTITLE_SELECT_GROUPS = SELECTOR_SUBTITLE_SELECT
SUBTITLE_SELECT_TO_ADD = SELECTOR_SUBTITLE_ADD
SUBTITLE_SELECT_TO_REMOVE = SELECTOR_SUBTITLE_REMOVE
SUBTITLE_CURRENT_GROUPS = SELECTOR_SUBTITLE_CURRENT
SUBTITLE_REPLACEMENT_GROUPS = SELECTOR_SUBTITLE_REPLACE
SUBTITLE_USERS_WITH_GROUPS = SELECTOR_SUBTITLE_SELECT


@dataclass(frozen=True)
class GroupOption:
    id: int
    name: str = ""

    @property
    def label(self) -> str:
        return str(self.id)


def groups_to_options(groups: Sequence) -> tuple[GroupOption, ...]:
    """Accept GroupInfo-like objects or raw ints."""
    options: list[GroupOption] = []
    for group in groups:
        if isinstance(group, GroupOption):
            options.append(group)
            continue
        if isinstance(group, int):
            options.append(GroupOption(id=group))
            continue
        group_id = int(getattr(group, "id"))
        name = str(getattr(group, "name", "") or "")
        options.append(GroupOption(id=group_id, name=name))
    return tuple(options)


def build_group_state(
    available_groups: Sequence,
    *,
    selected: Sequence[int] | None = None,
    multi_select: bool = True,
) -> SelectionState:
    options = groups_to_options(available_groups)
    items = tuple(SelectableItem(id=option.id, label=option.label) for option in options)
    initial = {int(value) for value in (selected or ())}
    available_ids = {item.id for item in items}
    initial &= available_ids
    return SelectionState(available=items, selected=initial, multi_select=multi_select)


def format_selected_groups_summary(state: SelectionState, *, empty: str = "—") -> list[str]:
    ids = [int(value) for value in state.selected_ids()]
    count = len(ids)
    if count == 0:
        return [SELECTOR_SELECTED, "0 Groups", empty]
    noun = "Group" if count == 1 else "Groups"
    return [SELECTOR_SELECTED, f"{count} {noun}", ", ".join(str(value) for value in ids)]


def format_group_selector_screen(
    *,
    title: str,
    subtitle: str,
    state: SelectionState,
    include_nav_hints: bool = False,
) -> list[str]:
    """Shared screen body for CLI and Telegram."""
    lines = [
        title,
        subtitle,
        *format_checklist(state),
        DIVIDER,
        *format_selected_groups_summary(state),
        DIVIDER,
    ]
    if include_nav_hints:
        lines.extend([TARGET_CONTINUE, BTN_BACK])
    return lines


def validate_group_selection(state: SelectionState, *, allow_empty: bool = False) -> str | None:
    error = validate_selection(state, allow_empty=allow_empty)
    if error == "empty":
        return MSG_SELECT_AT_LEAST_ONE_GROUP
    return error


def select_groups(
    *,
    title: str,
    subtitle: str,
    available_groups: Sequence,
    selected: Sequence[int] | None = None,
    multi_select: bool = True,
    allow_empty: bool = False,
) -> tuple[int, ...] | None:
    """CLI Group Selector. Returns selected IDs, or None if the user cancels."""
    from rich.prompt import Prompt

    from ...cli import theme

    state = build_group_state(
        available_groups, selected=selected, multi_select=multi_select
    )
    if not state.available:
        theme.notify_warning(SELECTOR_NO_GROUPS)
        theme.pause()
        return None

    while True:
        content = format_group_selector_screen(title=title, subtitle=subtitle, state=state)
        menu_items = [
            *((str(index), f"Toggle {item.label}") for index, item in enumerate(state.available, start=1)),
            ("c", TARGET_CONTINUE),
            ("0", BTN_BACK),
        ]
        # theme.page already renders the title header — body starts at subtitle.
        theme.page(
            title,
            theme.body_text(content[1:]),
            "",
            theme.option_menu(menu_items),
        )
        choices = [str(i) for i in range(1, len(state.available) + 1)] + ["c", "0"]
        choice = Prompt.ask(
            "\nSelect an option",
            choices=choices,
            default="c",
            show_choices=False,
        )
        if choice == "0":
            return None
        if choice == "c":
            error = validate_group_selection(state, allow_empty=allow_empty)
            if error:
                theme.notify_warning(error)
                theme.pause()
                continue
            return tuple(int(value) for value in state.selected_ids())
        item = state.available[int(choice) - 1]
        state.toggle(item.id)
