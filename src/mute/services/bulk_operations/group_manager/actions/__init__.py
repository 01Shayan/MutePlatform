"""Group Manager actions package."""

from .add import AddGroupIdsAction
from .base import ActionInfo, GroupAction, PlannedChange
from .remove import RemoveGroupIdsAction
from .replace import ReplaceGroupIdsAction


def default_actions() -> tuple[GroupAction, ...]:
    return (
        AddGroupIdsAction(),
        RemoveGroupIdsAction(),
        ReplaceGroupIdsAction(),
    )


__all__ = [
    "ActionInfo",
    "AddGroupIdsAction",
    "GroupAction",
    "PlannedChange",
    "RemoveGroupIdsAction",
    "ReplaceGroupIdsAction",
    "default_actions",
]
