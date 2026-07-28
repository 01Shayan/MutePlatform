"""Preview and Review screen formatters — shared by CLI and Telegram."""

from __future__ import annotations

from typing import Sequence

from ....ui.copy import (
    ACTION_SECTION,
    DIVIDER,
    LABEL_AVAILABLE_GROUPS,
    LABEL_MATCHED_USERS,
    LABEL_SNAPSHOT_USERS,
    MATCHED_SECTION,
    MSG_MATCHED_COUNT,
    MSG_NO_MATCHED,
    TARGET_SECTION,
    TITLE_GROUP_MANAGER,
)
from .target_rules import TargetRule, format_target_rules
from .working_set import WorkingSet, WorkingSetUser

DEFAULT_PREVIEW_LIMIT = 4


def preview_usernames(
    users: Sequence[WorkingSetUser] | WorkingSet,
    *,
    limit: int = DEFAULT_PREVIEW_LIMIT,
) -> tuple[tuple[str, ...], int]:
    """Return (preview names, remaining count beyond preview)."""
    if isinstance(users, WorkingSet):
        names = users.usernames()
    else:
        names = tuple(user.username for user in users)
    shown = names[: max(0, limit)]
    remaining = max(0, len(names) - len(shown))
    return shown, remaining


def format_query_preview(
    working_set: WorkingSet,
    *,
    rules: Sequence[TargetRule] | None = None,
    limit: int = DEFAULT_PREVIEW_LIMIT,
) -> list[str]:
    """Matched users preview with human-readable target rules."""
    shown, remaining = preview_usernames(working_set, limit=limit)
    lines = [TARGET_SECTION]
    if rules:
        lines.extend(format_target_rules(rules))
    else:
        lines.append("(selected)")
    lines.extend(["", MATCHED_SECTION, str(working_set.matched), "Preview"])
    if not shown:
        lines.append("(none)")
    else:
        lines.extend(shown)
        if remaining:
            lines.append(f"(+{remaining} more)")
    return lines


def format_review_screen(
    working_set: WorkingSet,
    *,
    action_label: str,
    group_ids: Sequence[int],
    rules: Sequence[TargetRule] | None = None,
    limit: int = DEFAULT_PREVIEW_LIMIT,
) -> list[str]:
    """Human-readable Review screen before Confirm / Cancel."""
    lines = [
        TARGET_SECTION,
        *(format_target_rules(rules) if rules else ["(selected)"]),
        DIVIDER,
        MATCHED_SECTION,
        str(working_set.matched),
        DIVIDER,
        ACTION_SECTION,
        action_label,
        *_id_lines(tuple(group_ids)),
        DIVIDER,
    ]
    return lines


def format_home_status(
    *,
    workspace: str,
    snapshot_users: int,
    available_groups: int,
    working_set_matched: int | None,
) -> list[str]:
    """Group Manager summary only (menus are rendered separately as actions)."""
    if working_set_matched is None:
        matched_line = f"{LABEL_MATCHED_USERS}: {MSG_NO_MATCHED}"
    else:
        matched_line = (
            f"{LABEL_MATCHED_USERS}: {MSG_MATCHED_COUNT.format(n=working_set_matched)}"
        )
    return [
        f"{TITLE_GROUP_MANAGER} — {workspace}",
        f"{LABEL_SNAPSHOT_USERS}: {snapshot_users}",
        f"{LABEL_AVAILABLE_GROUPS}: {available_groups}",
        matched_line,
        DIVIDER,
    ]


def _id_lines(values: tuple[int, ...] | Sequence[int]) -> list[str]:
    if not values:
        return ["—"]
    return [str(value) for value in values]
