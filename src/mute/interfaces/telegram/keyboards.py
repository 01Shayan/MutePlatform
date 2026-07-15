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
    rows.extend([[("Add Workspace", "future:add-workspace")], [("Back", "nav:back")]])
    return inline_keyboard(rows)


def dashboard_keyboard() -> InlineKeyboardMarkup:
    return inline_keyboard(
        [
            [("Backup", "backup:menu")],
            [("Group Checker", "future:group-checker")],
            [("Migration", "future:migration")],
            [("Edit Workspace", "future:edit-workspace")],
            [("Delete Workspace", "future:delete-workspace")],
            [("Back", "nav:back")],
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


def backup_history_keyboard() -> InlineKeyboardMarkup:
    """Read-only history view returns to the Backup page."""
    return inline_keyboard([[("Back", "backup:menu")]])


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


def delete_single_confirm_keyboard(archive_name: str) -> InlineKeyboardMarkup:
    return inline_keyboard(
        [[("Yes", f"backup:confirm-delete:{archive_name}")], [("No", "backup:delete-single")]]
    )


def delete_all_confirm_keyboard() -> InlineKeyboardMarkup:
    return inline_keyboard([[("Yes", "backup:confirm-delete-all")], [("No", "backup:delete")]])


def backup_result_keyboard(archive_name: str) -> InlineKeyboardMarkup:
    """The completed-export screen offers the single Download Backup action."""
    return inline_keyboard([[("Download Backup", f"backup:download:{archive_name}")]])


def backup_back_keyboard() -> InlineKeyboardMarkup:
    """A lone Back button returning to the refreshed Backup page."""
    return inline_keyboard([[("Back", "backup:menu")]])
