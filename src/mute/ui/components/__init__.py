"""Reusable UI components (selectors). Presentation only."""

from .group_selector import (
    GroupOption,
    SUBTITLE_CURRENT_GROUPS,
    SUBTITLE_REPLACEMENT_GROUPS,
    SUBTITLE_SELECT_GROUPS,
    SUBTITLE_SELECT_TO_ADD,
    SUBTITLE_SELECT_TO_REMOVE,
    SUBTITLE_USERS_WITH_GROUPS,
    build_group_state,
    format_group_selector_screen,
    select_groups,
    validate_group_selection,
)
from .selector import SelectableItem, SelectionState

__all__ = [
    "GroupOption",
    "SUBTITLE_CURRENT_GROUPS",
    "SUBTITLE_REPLACEMENT_GROUPS",
    "SUBTITLE_SELECT_GROUPS",
    "SUBTITLE_SELECT_TO_ADD",
    "SUBTITLE_SELECT_TO_REMOVE",
    "SUBTITLE_USERS_WITH_GROUPS",
    "SelectableItem",
    "SelectionState",
    "build_group_state",
    "format_group_selector_screen",
    "select_groups",
    "validate_group_selection",
]
