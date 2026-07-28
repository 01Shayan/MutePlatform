"""Tests for the shared Group Selector component."""

from __future__ import annotations

from mute.ui.components.group_selector import (
    SUBTITLE_SELECT_TO_ADD,
    build_group_state,
    format_group_selector_screen,
    validate_group_selection,
)
from mute.ui.copy import DIVIDER, MSG_SELECT_AT_LEAST_ONE_GROUP, SELECTOR_SELECTED


class _Group:
    def __init__(self, group_id: int):
        self.id = group_id
        self.name = f"g{group_id}"


def test_format_group_selector_screen_layout():
    state = build_group_state([_Group(3), _Group(4), _Group(9)], selected=(4, 9))
    lines = format_group_selector_screen(
        title="➕ Add Groups",
        subtitle=SUBTITLE_SELECT_TO_ADD,
        state=state,
    )
    assert lines[0] == "➕ Add Groups"
    assert lines[1] == SUBTITLE_SELECT_TO_ADD
    assert "☐ 3" in lines
    assert "☑ 4" in lines
    assert "☑ 9" in lines
    assert DIVIDER in lines
    assert SELECTOR_SELECTED in lines
    assert "2 Groups" in lines
    assert "4, 9" in lines


def test_validate_rejects_empty_selection():
    state = build_group_state([_Group(1), _Group(2)])
    assert validate_group_selection(state) == MSG_SELECT_AT_LEAST_ONE_GROUP


def test_validate_allows_empty_when_configured():
    state = build_group_state([_Group(1)])
    assert validate_group_selection(state, allow_empty=True) is None


def test_toggle_and_unknown_rejected():
    state = build_group_state([_Group(1), _Group(2)], selected=(1,))
    state.toggle(1)
    assert state.selected_ids() == ()
    state.toggle(2)
    assert state.selected_ids() == (2,)
    try:
        state.toggle(99)
        assert False, "expected ValueError"
    except ValueError:
        pass
