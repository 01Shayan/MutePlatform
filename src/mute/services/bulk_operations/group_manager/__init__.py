"""Group Manager — Snapshot, Filter, Matched Users, Actions, Execution Reports.

Users are never manually selected. Filter produces a Working Set; Actions operate
only on that Working Set. Snapshot is destroyed when leaving Group Manager.
"""

from .application_service import GroupManagerApplicationService
from .catalog import GroupCatalog, GroupInfo, format_available_groups
from .copy import (
    BTN_BACK_HOME,
    BTN_CANCEL,
    BTN_CONFIRM,
    BTN_DOWNLOAD,
    MENU_BACK,
    MENU_FILTER_USERS,
    MENU_REFRESH,
    MENU_VIEW_MATCHED,
)
from .errors import GroupManagerError
from .ids import format_group_ids, parse_group_ids
from .preview import format_home_status, format_query_preview, format_review_screen, preview_usernames
from .query import GroupQuery, MatchMode
from .reports import ExecutionReport, ResultEntry, format_duration_seconds, list_reports
from .snapshot import GroupSnapshot, SnapshotUser
from .target_rules import TargetRule, TargetRuleKind, compile_target_rules, format_target_rules
from .working_set import WorkingSet, WorkingSetUser

__all__ = [
    "BTN_BACK_HOME",
    "BTN_CANCEL",
    "BTN_CONFIRM",
    "BTN_DOWNLOAD",
    "ExecutionReport",
    "GroupCatalog",
    "GroupInfo",
    "GroupManagerApplicationService",
    "GroupManagerError",
    "GroupQuery",
    "GroupSnapshot",
    "MENU_BACK",
    "MENU_FILTER_USERS",
    "MENU_REFRESH",
    "MENU_VIEW_MATCHED",
    "MatchMode",
    "ResultEntry",
    "SnapshotUser",
    "TargetRule",
    "TargetRuleKind",
    "WorkingSet",
    "WorkingSetUser",
    "compile_target_rules",
    "format_available_groups",
    "format_duration_seconds",
    "format_group_ids",
    "format_home_status",
    "format_query_preview",
    "format_review_screen",
    "format_target_rules",
    "list_reports",
    "parse_group_ids",
    "preview_usernames",
]
