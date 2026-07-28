"""Platform-wide UI copy — one concept, one name. Used by CLI and Telegram."""

from __future__ import annotations

from .icons import Icon
from .layout import DIVIDER

__all__ = [
    "DIVIDER",
    "BTN_BACK",
    "BTN_CANCEL",
    "BTN_CONFIRM",
    "BTN_HOME",
    "BTN_YES",
    "BTN_NO",
    "MSG_LOADING",
    "MSG_CANCELLED",
    "MSG_SUCCESS_GENERIC",
    "MSG_FAILED_GENERIC",
    "MSG_WARNING_NO_MATCH",
    "MSG_INFO_REFRESH_OK",
    "TITLE_HOME",
    "MENU_MY_WORKSPACES",
    "MENU_SETTINGS",
    "MENU_ABOUT",
    "MENU_EXIT",
    "MENU_BACKUP",
    "MENU_BULK_OPS",
    "MENU_MIGRATION",
    "MENU_EDIT_WORKSPACE",
    "MENU_DELETE_WORKSPACE",
    "MENU_ADD_WORKSPACE",
    "TITLE_SETTINGS",
    "SETTINGS_INTRO",
    "MENU_RESET_TOKENS",
    "MENU_CHANGE_BOT_TOKEN",
    "MENU_CHANGE_OWNER_IDS",
    "TITLE_BACKUP",
    "MENU_CREATE_EXPORT",
    "MENU_BACKUP_HISTORY",
    "MENU_DELETE_BACKUP",
    "MENU_DELETE_SINGLE",
    "MENU_DELETE_ALL",
    "MENU_DOWNLOAD_BACKUP",
    "MSG_BACKUP_DONE",
    "MSG_BACKUP_LOADING_USERS",
    "MSG_BACKUP_WRITING",
    "TITLE_BULK_OPS",
    "BULK_OPS_INTRO",
    "MENU_GROUP_MANAGER",
    "TITLE_GROUP_MANAGER",
    "LABEL_SNAPSHOT_USERS",
    "LABEL_AVAILABLE_GROUPS",
    "LABEL_MATCHED_USERS",
    "MENU_SELECT_TARGET",
    "MENU_FILTER_USERS",
    "MENU_VIEW_MATCHED",
    "MENU_REFRESH_SNAPSHOT",
    "TARGET_TITLE",
    "TARGET_ALL_USERS",
    "TARGET_WITH_GROUPS",
    "TARGET_WITHOUT_GROUPS",
    "TARGET_SELECT_GROUPS",
    "TARGET_REQUIRE_ALL",
    "TARGET_REQUIRE_ANY",
    "TARGET_ADD_RULE",
    "TARGET_CONTINUE",
    "TARGET_CURRENT",
    "TARGET_SECTION",
    "SELECTOR_SELECTED",
    "SELECTOR_SUBTITLE_SELECT",
    "SELECTOR_SUBTITLE_ADD",
    "SELECTOR_SUBTITLE_REMOVE",
    "SELECTOR_SUBTITLE_CURRENT",
    "SELECTOR_SUBTITLE_REPLACE",
    "SELECTOR_NO_GROUPS",
    "FILTER_TITLE",
    "MATCHED_TITLE",
    "REVIEW_TITLE",
    "FILTER_SECTION",
    "MATCHED_SECTION",
    "ACTION_SECTION",
    "ACTIONS_SECTION",
    "BTN_DOWNLOAD_REPORT",
    "ACTION_ADD_GROUPS",
    "ACTION_REMOVE_GROUPS",
    "ACTION_REPLACE_GROUPS",
    "STATUS_LOADING_SNAPSHOT",
    "STATUS_REFRESHING",
    "STATUS_USERS_LOADED",
    "STATUS_GROUPS_LOADED",
    "STATUS_REFRESH_OK",
    "STATUS_FILTER_CLEARED",
    "STATUS_MATCHED_RESET",
    "STATUS_EXECUTING",
    "STATUS_NO_CANCEL",
    "STATUS_COMPLETED",
    "MSG_NO_MATCHED",
    "MSG_MATCHED_COUNT",
    "MSG_NO_USERS_MATCHED",
    "MSG_SELECT_AT_LEAST_ONE_GROUP",
    "REPORT_SUMMARY_TITLE",
    "REPORT_MATCHED",
    "REPORT_SUCCESS",
    "REPORT_FAILED",
    "REPORT_DURATION",
    "LABEL_AVAILABLE_GROUPS_BLOCK",
]


# -- Navigation -----------------------------------------------------------------------

BTN_BACK = f"{Icon.HOME} Back"
BTN_HOME = f"{Icon.HOME} Home"
BTN_CANCEL = f"{Icon.CANCEL} Cancel"
BTN_CONFIRM = f"{Icon.CONFIRM} Confirm"
BTN_YES = f"{Icon.CONFIRM} Yes"
BTN_NO = f"{Icon.CANCEL} No"


# -- Status messages ------------------------------------------------------------------

MSG_LOADING = f"{Icon.LOADING} Loading..."
MSG_CANCELLED = f"{Icon.INFO} Cancelled."
MSG_SUCCESS_GENERIC = f"{Icon.SUCCESS} Operation completed successfully."
MSG_FAILED_GENERIC = f"{Icon.FAILED} Operation failed."
MSG_WARNING_NO_MATCH = f"{Icon.WARNING} No users matched your filter."
MSG_INFO_REFRESH_OK = f"{Icon.INFO} Snapshot refreshed successfully."


# -- Home -----------------------------------------------------------------------------

TITLE_HOME = f"{Icon.HOME} Home"
MENU_MY_WORKSPACES = f"{Icon.WORKSPACES} My Workspaces"
MENU_SETTINGS = f"{Icon.SETTINGS} Settings"
MENU_ABOUT = f"{Icon.INFO} About"
MENU_EXIT = f"{Icon.CANCEL} Exit"


# -- Dashboard / workspaces -----------------------------------------------------------

MENU_BACKUP = f"{Icon.BACKUP} Backup"
MENU_BULK_OPS = f"{Icon.BULK} Bulk Operations"
MENU_MIGRATION = f"{Icon.MIGRATION} Migration"
MENU_EDIT_WORKSPACE = "Edit Workspace"
MENU_DELETE_WORKSPACE = f"{Icon.FAILED} Delete Workspace"
MENU_ADD_WORKSPACE = f"{Icon.ADD} Add Workspace"


# -- Settings -------------------------------------------------------------------------

TITLE_SETTINGS = f"{Icon.SETTINGS} Settings"
SETTINGS_INTRO = "Manage Telegram and workspace credentials."
MENU_RESET_TOKENS = "Reset Workspace Tokens"
MENU_CHANGE_BOT_TOKEN = "Change Bot Token"
MENU_CHANGE_OWNER_IDS = "Change Owner IDs"


# -- Backup ---------------------------------------------------------------------------

TITLE_BACKUP = f"{Icon.BACKUP} Backup"
MENU_CREATE_EXPORT = f"{Icon.ADD} Create Export"
MENU_BACKUP_HISTORY = f"{Icon.HISTORY} Backup History"
MENU_DELETE_BACKUP = f"{Icon.FAILED} Delete Backup"
MENU_DELETE_SINGLE = "Delete Single Backup"
MENU_DELETE_ALL = "Delete All Backups"
MENU_DOWNLOAD_BACKUP = f"{Icon.DOWNLOAD} Download Backup"
MSG_BACKUP_DONE = f"{Icon.SUCCESS} Backup completed successfully."
MSG_BACKUP_LOADING_USERS = f"{Icon.LOADING} Loading users..."
MSG_BACKUP_WRITING = f"{Icon.LOADING} Writing backup..."


# -- Bulk Operations ------------------------------------------------------------------

TITLE_BULK_OPS = f"{Icon.BULK} Bulk Operations"
BULK_OPS_INTRO = (
    "Home for bulk modification workflows.\n"
    "Each manager owns one domain of panel changes."
)
MENU_GROUP_MANAGER = f"{Icon.USERS} Group Manager"


# -- Group Manager --------------------------------------------------------------------

TITLE_GROUP_MANAGER = f"{Icon.USERS} Group Manager"
LABEL_SNAPSHOT_USERS = f"{Icon.SNAPSHOT} Snapshot Users"
LABEL_AVAILABLE_GROUPS = f"{Icon.GROUPS} Available Groups"
LABEL_MATCHED_USERS = f"{Icon.USERS} Matched Users"

MENU_SELECT_TARGET = "🎯 Select Target Users"
MENU_FILTER_USERS = MENU_SELECT_TARGET  # legacy alias
MENU_VIEW_MATCHED = f"{Icon.USERS} View Matched Users"
MENU_REFRESH_SNAPSHOT = f"{Icon.REFRESH} Refresh Snapshot"

TARGET_TITLE = MENU_SELECT_TARGET
TARGET_ALL_USERS = "🌐 All Snapshot Users"
TARGET_WITH_GROUPS = "🏷 Users with Groups"
TARGET_WITHOUT_GROUPS = "🚫 Users without Groups"
TARGET_SELECT_GROUPS = "Select Groups"
TARGET_REQUIRE_ALL = "All selected groups"
TARGET_REQUIRE_ANY = "Any selected group"
TARGET_ADD_RULE = "➕ Add Another Rule"
TARGET_CONTINUE = "➡ Continue"
TARGET_CURRENT = "Current Target"
TARGET_SECTION = "📋 Target Users"

SELECTOR_SELECTED = "Selected"
SELECTOR_SUBTITLE_SELECT = "Select Groups"
SELECTOR_SUBTITLE_ADD = "Select Groups to Add"
SELECTOR_SUBTITLE_REMOVE = "Select Groups to Remove"
SELECTOR_SUBTITLE_CURRENT = "Current Groups"
SELECTOR_SUBTITLE_REPLACE = "Replacement Groups"
SELECTOR_NO_GROUPS = "No groups available."

FILTER_TITLE = TARGET_TITLE
MATCHED_TITLE = MENU_VIEW_MATCHED
REVIEW_TITLE = f"{Icon.REVIEW} Review"
FILTER_SECTION = TARGET_SECTION
MATCHED_SECTION = LABEL_MATCHED_USERS
ACTION_SECTION = f"{Icon.ACTIONS} Action"
ACTIONS_SECTION = f"{Icon.ACTIONS} Actions"

BTN_DOWNLOAD_REPORT = f"{Icon.DOWNLOAD} Download Report"

ACTION_ADD_GROUPS = f"{Icon.ADD} Add Groups"
ACTION_REMOVE_GROUPS = f"{Icon.REMOVE} Remove Groups"
ACTION_REPLACE_GROUPS = f"{Icon.REPLACE} Replace Groups"

STATUS_LOADING_SNAPSHOT = f"{Icon.LOADING} Loading Catalog + Snapshot..."
STATUS_REFRESHING = f"{Icon.REFRESH} Refreshing Snapshot..."
STATUS_USERS_LOADED = "✓ Users loaded"
STATUS_GROUPS_LOADED = "✓ Groups loaded"
STATUS_REFRESH_OK = MSG_INFO_REFRESH_OK
STATUS_FILTER_CLEARED = "Target selection cleared."
STATUS_MATCHED_RESET = "Matched Users reset."
STATUS_EXECUTING = f"{Icon.EXECUTING} Executing..."
STATUS_NO_CANCEL = "Operation cannot be cancelled."
STATUS_COMPLETED = f"{Icon.SUCCESS} Operation completed successfully."

MSG_NO_MATCHED = "none — select target users first"
MSG_MATCHED_COUNT = "{n} matched"
MSG_NO_USERS_MATCHED = MSG_WARNING_NO_MATCH
MSG_SELECT_AT_LEAST_ONE_GROUP = f"{Icon.WARNING} Select at least one group."

REPORT_SUMMARY_TITLE = f"{Icon.REPORT} Report Summary"
REPORT_MATCHED = f"{Icon.USERS} Matched Users"
REPORT_SUCCESS = f"{Icon.SUCCESS} Success"
REPORT_FAILED = f"{Icon.FAILED} Failed"
REPORT_DURATION = f"{Icon.DURATION} Duration"

LABEL_AVAILABLE_GROUPS_BLOCK = "Available Groups"
PROMPT_ACTION_IDS = "Enter Group IDs for this action."  # deprecated — use Group Selector
PROMPT_GROUP_IDS = "Group IDs"  # deprecated — use Group Selector
