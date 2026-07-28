"""Reusable Telegram keyboard builders — labels from the Design System (mirrors CLI)."""

from __future__ import annotations

from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from ...ui.copy import (
    BTN_BACK,
    BTN_CANCEL,
    BTN_CHANGE_INTERVAL,
    BTN_CHANGE_LIMIT,
    BTN_CONFIRM,
    BTN_DISABLE,
    BTN_DOWNLOAD_REPORT,
    BTN_ENABLE,
    BTN_NO,
    BTN_YES,
    MENU_ABOUT,
    MENU_ADD_WORKSPACE,
    MENU_AUTO_BACKUP,
    MENU_BACKUP,
    MENU_BACKUP_HISTORY,
    MENU_BULK_OPS,
    MENU_CHANGE_BOT_TOKEN,
    MENU_CHANGE_OWNER_IDS,
    MENU_CREATE_EXPORT,
    MENU_DELETE_ALL,
    MENU_DELETE_BACKUP,
    MENU_DELETE_SINGLE,
    MENU_DELETE_WORKSPACE,
    MENU_DOWNLOAD_BACKUP,
    MENU_EDIT_WORKSPACE,
    MENU_GROUP_MANAGER,
    MENU_MAX_BACKUPS,
    MENU_MIGRATION,
    MENU_MY_WORKSPACES,
    MENU_REFRESH_SNAPSHOT,
    MENU_RESET_TOKENS,
    MENU_SELECT_TARGET,
    MENU_SETTINGS,
    MENU_VIEW_MATCHED,
    TARGET_ADD_RULE,
    TARGET_ALL_USERS,
    TARGET_CONTINUE,
    TARGET_REQUIRE_ALL,
    TARGET_REQUIRE_ANY,
    TARGET_WITH_GROUPS,
    TARGET_WITHOUT_GROUPS,
)


def inline_keyboard(rows: list[list[tuple[str, str]]]) -> InlineKeyboardMarkup:
    """Build an inline keyboard from ``(label, callback_data)`` pairs."""
    return InlineKeyboardMarkup(
        [[InlineKeyboardButton(label, callback_data=data) for label, data in row] for row in rows]
    )


def home_keyboard() -> InlineKeyboardMarkup:
    return inline_keyboard(
        [
            [(MENU_MY_WORKSPACES, "nav:workspaces")],
            [(MENU_SETTINGS, "nav:settings")],
            [(MENU_ABOUT, "nav:about")],
        ]
    )


def workspaces_keyboard(workspace_names: list[str]) -> InlineKeyboardMarkup:
    rows = [[(name, f"workspace:{name}")] for name in workspace_names]
    rows.extend([[(MENU_ADD_WORKSPACE, "ws:add")], [(BTN_BACK, "nav:back")]])
    return inline_keyboard(rows)


def dashboard_keyboard() -> InlineKeyboardMarkup:
    return inline_keyboard(
        [
            [(MENU_BACKUP, "backup:menu")],
            [(MENU_BULK_OPS, "bulk:menu")],
            [(MENU_MIGRATION, "future:migration")],
            [(MENU_EDIT_WORKSPACE, "ws:edit")],
            [(MENU_DELETE_WORKSPACE, "ws:delete")],
            [(BTN_BACK, "nav:back")],
        ]
    )


def settings_keyboard() -> InlineKeyboardMarkup:
    return inline_keyboard(
        [
            [(MENU_RESET_TOKENS, "settings:reset-tokens")],
            [(MENU_CHANGE_BOT_TOKEN, "settings:bot-token")],
            [(MENU_CHANGE_OWNER_IDS, "settings:owner-ids")],
            [(BTN_BACK, "nav:back")],
        ]
    )


def yes_no_keyboard(yes_data: str, no_data: str) -> InlineKeyboardMarkup:
    return inline_keyboard([[(BTN_YES, yes_data), (BTN_NO, no_data)]])


def cancel_keyboard(cancel_data: str) -> InlineKeyboardMarkup:
    return inline_keyboard([[(BTN_CANCEL, cancel_data)]])


def integrations_keyboard(items: list[tuple[str, str, bool]]) -> InlineKeyboardMarkup:
    """Build integration choices: ``(key, label, available)``."""
    rows = []
    for key, label, available in items:
        if available:
            rows.append([(label, f"ws:integration:{key}")])
        else:
            rows.append([(f"{label} (coming soon)", f"ws:integration-soon:{key}")])
    rows.append([(BTN_CANCEL, "ws:cancel")])
    return inline_keyboard(rows)


def auth_method_keyboard(*, cancel_data: str = "ws:cancel") -> InlineKeyboardMarkup:
    return inline_keyboard(
        [
            [("Username / Password", "ws:auth:password")],
            [("Bearer Token", "ws:auth:token")],
            [(BTN_CANCEL, cancel_data)],
        ]
    )


def verify_ssl_keyboard(*, cancel_data: str = "ws:cancel") -> InlineKeyboardMarkup:
    return inline_keyboard(
        [
            [(BTN_YES, "ws:ssl:yes"), (BTN_NO, "ws:ssl:no")],
            [(BTN_CANCEL, cancel_data)],
        ]
    )


def back_keyboard() -> InlineKeyboardMarkup:
    return inline_keyboard([[(BTN_BACK, "nav:back")]])


def backup_menu_keyboard() -> InlineKeyboardMarkup:
    return inline_keyboard(
        [
            [(MENU_CREATE_EXPORT, "backup:create")],
            [(MENU_AUTO_BACKUP, "backup:auto")],
            [(MENU_MAX_BACKUPS, "backup:max")],
            [(MENU_BACKUP_HISTORY, "backup:history")],
            [(MENU_DELETE_BACKUP, "backup:delete")],
            [(BTN_BACK, "backup:dashboard")],
        ]
    )


def auto_backup_keyboard(*, enabled: bool) -> InlineKeyboardMarkup:
    if enabled:
        rows = [
            [(BTN_CHANGE_INTERVAL, "backup:auto:interval")],
            [(BTN_DISABLE, "backup:auto:disable")],
            [(BTN_BACK, "backup:menu")],
        ]
    else:
        rows = [
            [(BTN_ENABLE, "backup:auto:enable")],
            [(BTN_BACK, "backup:menu")],
        ]
    return inline_keyboard(rows)


def max_backups_keyboard() -> InlineKeyboardMarkup:
    return inline_keyboard(
        [
            [(BTN_CHANGE_LIMIT, "backup:max:change")],
            [(BTN_BACK, "backup:menu")],
        ]
    )


def backup_history_keyboard(archive_names: list[str]) -> InlineKeyboardMarkup:
    rows = [[(name, f"backup:archive:{name}")] for name in archive_names]
    rows.append([(BTN_BACK, "backup:menu")])
    return inline_keyboard(rows)


def archive_details_keyboard(archive_name: str) -> InlineKeyboardMarkup:
    return inline_keyboard(
        [
            [(MENU_DOWNLOAD_BACKUP, f"backup:download:{archive_name}")],
            [(MENU_DELETE_BACKUP, f"backup:delete:{archive_name}")],
            [(BTN_BACK, "backup:history")],
        ]
    )


def delete_menu_keyboard() -> InlineKeyboardMarkup:
    return inline_keyboard(
        [
            [(MENU_DELETE_SINGLE, "backup:delete-single")],
            [(MENU_DELETE_ALL, "backup:delete-all")],
            [(BTN_BACK, "backup:menu")],
        ]
    )


def delete_single_list_keyboard(archive_names: list[str]) -> InlineKeyboardMarkup:
    rows = [[(name, f"backup:delete:{name}")] for name in archive_names]
    rows.append([(BTN_BACK, "backup:delete")])
    return inline_keyboard(rows)


def delete_single_confirm_keyboard(
    archive_name: str, *, no_data: str = "backup:delete-single"
) -> InlineKeyboardMarkup:
    return yes_no_keyboard(f"backup:confirm-delete:{archive_name}", no_data)


def delete_all_confirm_keyboard() -> InlineKeyboardMarkup:
    return yes_no_keyboard("backup:confirm-delete-all", "backup:delete")


def backup_result_keyboard(archive_name: str) -> InlineKeyboardMarkup:
    return inline_keyboard(
        [
            [(MENU_DOWNLOAD_BACKUP, f"backup:download:{archive_name}")],
            [(BTN_BACK, "backup:dashboard")],
        ]
    )


def backup_back_keyboard() -> InlineKeyboardMarkup:
    return inline_keyboard([[(BTN_BACK, "backup:menu")]])


def bulk_ops_keyboard() -> InlineKeyboardMarkup:
    return inline_keyboard(
        [
            [(MENU_GROUP_MANAGER, "bulk:group_manager")],
            [(BTN_BACK, "bulk:dashboard")],
        ]
    )


def gm_menu_keyboard(*, has_working_set: bool) -> InlineKeyboardMarkup:
    rows = [[(MENU_SELECT_TARGET, "gm:query")]]
    if has_working_set:
        rows.append([(MENU_VIEW_MATCHED, "gm:working_set")])
    rows.append([(MENU_REFRESH_SNAPSHOT, "gm:refresh")])
    rows.append([(BTN_BACK, "bulk:menu")])
    return inline_keyboard(rows)


def gm_result_back_keyboard() -> InlineKeyboardMarkup:
    return inline_keyboard([[(BTN_BACK, "gm:back_manager")]])


def gm_target_menu_keyboard() -> InlineKeyboardMarkup:
    return inline_keyboard(
        [
            [(TARGET_ALL_USERS, "gm:target:all")],
            [(TARGET_WITH_GROUPS, "gm:target:with")],
            [(TARGET_WITHOUT_GROUPS, "gm:target:without")],
            [(BTN_BACK, "gm:back_manager")],
        ]
    )


def gm_group_selector_keyboard(
    groups,
    selected_ids: set[int] | list[int],
    *,
    toggle_prefix: str = "gm:toggle:",
    done_callback: str = "gm:groups_done",
    back_callback: str = "gm:target_menu",
) -> InlineKeyboardMarkup:
    """Shared Group Selector keyboard (Target Selection + Actions)."""
    selected = set(selected_ids)
    rows = []
    for group in groups:
        mark = "☑" if group.id in selected else "☐"
        rows.append([(f"{mark} {group.id}", f"{toggle_prefix}{group.id}")])
    rows.append([(TARGET_CONTINUE, done_callback)])
    rows.append([(BTN_BACK, back_callback)])
    return inline_keyboard(rows)


def gm_target_groups_keyboard(groups, selected_ids: set[int] | list[int]) -> InlineKeyboardMarkup:
    return gm_group_selector_keyboard(
        groups,
        selected_ids,
        toggle_prefix="gm:toggle:",
        done_callback="gm:groups_done",
        back_callback="gm:target_menu",
    )


def gm_action_groups_keyboard(groups, selected_ids: set[int] | list[int]) -> InlineKeyboardMarkup:
    return gm_group_selector_keyboard(
        groups,
        selected_ids,
        toggle_prefix="gm:asel:",
        done_callback="gm:action_done",
        back_callback="gm:working_set",
    )


def gm_target_require_keyboard() -> InlineKeyboardMarkup:
    return inline_keyboard(
        [
            [(TARGET_REQUIRE_ALL, "gm:require:all")],
            [(TARGET_REQUIRE_ANY, "gm:require:any")],
            [(BTN_BACK, "gm:target_menu")],
        ]
    )


def gm_target_rules_keyboard() -> InlineKeyboardMarkup:
    return inline_keyboard(
        [
            [(TARGET_ADD_RULE, "gm:add_rule")],
            [(TARGET_CONTINUE, "gm:apply_rules")],
            [(BTN_BACK, "gm:back_manager")],
        ]
    )


def gm_actions_keyboard(actions) -> InlineKeyboardMarkup:
    rows = [[(info.label, f"gm:action:{info.id}")] for info in actions]
    rows.append([(BTN_BACK, "gm:back_manager")])
    return inline_keyboard(rows)


def gm_action_confirm_keyboard() -> InlineKeyboardMarkup:
    return inline_keyboard([[(BTN_CONFIRM, "gm:confirm"), (BTN_CANCEL, "gm:back_manager")]])


def gm_report_keyboard(filename: str) -> InlineKeyboardMarkup:
    rows = []
    if filename:
        rows.append([(BTN_DOWNLOAD_REPORT, f"gm:download:{filename}")])
    rows.append([(BTN_BACK, "gm:back_manager")])
    return inline_keyboard(rows)
