"""Reusable Telegram keyboard builders.

Feature-specific buttons belong in later phases; this module owns their construction.
"""

from __future__ import annotations

from telegram import InlineKeyboardButton, InlineKeyboardMarkup


def inline_keyboard(rows: list[list[tuple[str, str]]]) -> InlineKeyboardMarkup:
    """Build an inline keyboard from ``(label, callback_data)`` pairs."""
    return InlineKeyboardMarkup(
        [[InlineKeyboardButton(label, callback_data=data) for label, data in row] for row in rows]
    )


def home_keyboard() -> InlineKeyboardMarkup:
    return inline_keyboard(
        [[("My Workspaces", "nav:workspaces")], [("Settings", "nav:settings")], [("About", "nav:about")]]
    )


def workspaces_keyboard(workspace_names: list[str]) -> InlineKeyboardMarkup:
    rows = [[(name, f"workspace:{name}")] for name in workspace_names]
    rows.extend([[("Add Workspace", "ws:add")], [("Back", "nav:back")]])
    return inline_keyboard(rows)


def dashboard_keyboard() -> InlineKeyboardMarkup:
    return inline_keyboard(
        [
            [("Backup", "backup:menu")],
            [("Group Engine", "group_checker:menu")],
            [("Migration", "future:migration")],
            [("Edit Workspace", "ws:edit")],
            [("Delete Workspace", "ws:delete")],
            [("Back", "nav:back")],
        ]
    )


def settings_keyboard() -> InlineKeyboardMarkup:
    return inline_keyboard(
        [
            [("Reset Workspace Tokens", "settings:reset-tokens")],
            [("Change Bot Token", "settings:bot-token")],
            [("Change Owner IDs", "settings:owner-ids")],
            [("Back", "nav:back")],
        ]
    )


def yes_no_keyboard(yes_data: str, no_data: str) -> InlineKeyboardMarkup:
    return inline_keyboard([[("Yes", yes_data), ("No", no_data)]])


def cancel_keyboard(cancel_data: str) -> InlineKeyboardMarkup:
    return inline_keyboard([[("Cancel", cancel_data)]])


def integrations_keyboard(items: list[tuple[str, str, bool]]) -> InlineKeyboardMarkup:
    """Build integration choices: ``(key, label, available)``."""
    rows = []
    for key, label, available in items:
        if available:
            rows.append([(label, f"ws:integration:{key}")])
        else:
            rows.append([(f"{label} (coming soon)", f"ws:integration-soon:{key}")])
    rows.append([("Cancel", "ws:cancel")])
    return inline_keyboard(rows)


def auth_method_keyboard(*, cancel_data: str = "ws:cancel") -> InlineKeyboardMarkup:
    return inline_keyboard(
        [
            [("Username / Password", "ws:auth:password")],
            [("Bearer Token", "ws:auth:token")],
            [("Cancel", cancel_data)],
        ]
    )


def verify_ssl_keyboard(*, cancel_data: str = "ws:cancel") -> InlineKeyboardMarkup:
    return inline_keyboard(
        [
            [("Yes", "ws:ssl:yes"), ("No", "ws:ssl:no")],
            [("Cancel", cancel_data)],
        ]
    )


def back_keyboard() -> InlineKeyboardMarkup:
    return inline_keyboard([[("Back", "nav:back")]])


def backup_menu_keyboard() -> InlineKeyboardMarkup:
    """The Backup page menu, mirroring the CLI options."""
    return inline_keyboard(
        [
            [("Create Export", "backup:create")],
            [("Backup History", "backup:history")],
            [("Delete Backup", "backup:delete")],
            [("Back", "backup:dashboard")],
        ]
    )


def backup_history_keyboard(archive_names: list[str]) -> InlineKeyboardMarkup:
    """History list: one button per archive, then Back to the Backup menu."""
    rows = [[(name, f"backup:archive:{name}")] for name in archive_names]
    rows.append([("Back", "backup:menu")])
    return inline_keyboard(rows)


def archive_details_keyboard(archive_name: str) -> InlineKeyboardMarkup:
    """Archive Details actions — Download, Delete, or Back to History."""
    return inline_keyboard(
        [
            [("Download Backup", f"backup:download:{archive_name}")],
            [("Delete Backup", f"backup:delete:{archive_name}")],
            [("Back", "backup:history")],
        ]
    )


def delete_menu_keyboard() -> InlineKeyboardMarkup:
    return inline_keyboard(
        [
            [("Delete Single Backup", "backup:delete-single")],
            [("Delete All Backups", "backup:delete-all")],
            [("Back", "backup:menu")],
        ]
    )


def delete_single_list_keyboard(archive_names: list[str]) -> InlineKeyboardMarkup:
    """One button per archive, selecting it opens a delete confirmation."""
    rows = [[(name, f"backup:delete:{name}")] for name in archive_names]
    rows.append([("Back", "backup:delete")])
    return inline_keyboard(rows)


def delete_single_confirm_keyboard(
    archive_name: str, *, no_data: str = "backup:delete-single"
) -> InlineKeyboardMarkup:
    return inline_keyboard(
        [[("Yes", f"backup:confirm-delete:{archive_name}")], [("No", no_data)]]
    )


def delete_all_confirm_keyboard() -> InlineKeyboardMarkup:
    return inline_keyboard([[("Yes", "backup:confirm-delete-all")], [("No", "backup:delete")]])


def backup_result_keyboard(archive_name: str) -> InlineKeyboardMarkup:
    """Completed-export screen: optional download, or Back to the workspace dashboard."""
    return inline_keyboard(
        [
            [("Download Backup", f"backup:download:{archive_name}")],
            [("Back", "backup:dashboard")],
        ]
    )


def backup_back_keyboard() -> InlineKeyboardMarkup:
    """A lone Back button returning to the refreshed Backup page."""
    return inline_keyboard([[("Back", "backup:menu")]])


def group_checker_menu_keyboard() -> InlineKeyboardMarkup:
    """Group Engine menu — mirrors the CLI operation list."""
    return inline_keyboard(
        [
            [("Check", "group_checker:run")],
            [("Add", "group_checker:soon:add")],
            [("Remove", "group_checker:soon:remove")],
            [("Replace", "group_checker:soon:replace")],
            [("History", "group_checker:soon:history")],
            [("Back", "group_checker:dashboard")],
        ]
    )


def group_checker_coming_soon_keyboard() -> InlineKeyboardMarkup:
    return inline_keyboard([[("Back", "group_checker:menu")]])


def group_checker_backups_keyboard(backup_names: list[str]) -> InlineKeyboardMarkup:
    rows = [[(name, f"group_checker:backup:{name}")] for name in backup_names]
    rows.append([("Back", "group_checker:menu")])
    return inline_keyboard(rows)


def group_checker_query_keyboard(backup_name: str) -> InlineKeyboardMarkup:
    return inline_keyboard(
        [
            [("Required Groups", f"group_checker:query:{backup_name}")],
            [("Back", "group_checker:run")],
        ]
    )


def group_checker_confirm_keyboard() -> InlineKeyboardMarkup:
    return inline_keyboard(
        [[("Yes", "group_checker:confirm")], [("No", "group_checker:run")]]
    )


def group_checker_result_keyboard() -> InlineKeyboardMarkup:
    return inline_keyboard([[("Back", "group_checker:menu")]])


def group_checker_input_keyboard() -> InlineKeyboardMarkup:
    return inline_keyboard([[("Cancel", "group_checker:run")]])
