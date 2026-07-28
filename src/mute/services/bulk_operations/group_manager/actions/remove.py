"""Remove Groups action."""

from __future__ import annotations

from typing import Any, Mapping, Sequence

from ..ids import parse_group_ids
from ..working_set import WorkingSetUser
from .base import GroupAction, PlannedChange
from .....ui.copy import ACTION_REMOVE_GROUPS


class RemoveGroupIdsAction(GroupAction):
    id = "remove"
    label = ACTION_REMOVE_GROUPS
    description = "Remove group IDs from every matched user in the current Working Set."
    report_action = "remove_groups"
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
        remove = set(group_ids)
        planned: list[PlannedChange] = []
        for user in users:
            before = tuple(user.group_ids)
            after = tuple(sorted(set(before) - remove))
            planned.append(PlannedChange(username=user.username, before=before, after=after))
        return planned
