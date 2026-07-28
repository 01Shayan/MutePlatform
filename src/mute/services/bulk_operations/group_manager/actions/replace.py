"""Replace Groups action."""

from __future__ import annotations

from typing import Any, Mapping, Sequence

from ..ids import parse_group_ids
from ..working_set import WorkingSetUser
from .base import GroupAction, PlannedChange
from .....ui.copy import ACTION_REPLACE_GROUPS


class ReplaceGroupIdsAction(GroupAction):
    id = "replace"
    label = ACTION_REPLACE_GROUPS
    description = "Replace group membership for every matched user in the current Working Set."
    report_action = "replace_groups"
    available = True

    def validate_parameters(self, parameters: Mapping[str, Any]) -> tuple[int, ...]:
        raw = parameters.get("group_ids")
        if isinstance(raw, str):
            return parse_group_ids(raw)
        if isinstance(raw, (list, tuple)):
            return tuple(int(value) for value in raw)
        raise ValueError("group_ids is required.")

    def plan(
        self, users: Sequence[WorkingSetUser], group_ids: Sequence[int]
    ) -> list[PlannedChange]:
        after = tuple(sorted(set(int(value) for value in group_ids)))
        return [
            PlannedChange(username=user.username, before=tuple(user.group_ids), after=after)
            for user in users
        ]
