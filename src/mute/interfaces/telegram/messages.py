"""Shared Telegram message templates."""

from __future__ import annotations

from ...core.constants import APP_NAME, DEVELOPER, FOOTER_TEXT, GITHUB_URL, TAGLINE, VERSION
from ...core.timefmt import relative_time
from ...services.workspace import ConnectionStatus, WorkspaceApplicationService, WorkspaceNavigationItem
from ...services.backup import BackupArchive, BackupSummary, archive_display, format_duration, format_size
from ...services.group_checker import BackupSource, GroupCheckerResult, format_group_ids

_HOME_DIVIDER = "--------------------------------"


def home() -> str:
    """Home screen text — mirrors the CLI brand banner, menu, and footer."""
    return "\n".join(
        [
            f"🧠 {APP_NAME}",
            "",
            TAGLINE,
            "",
            "Current Version",
            f"v{VERSION}",
            "",
            _HOME_DIVIDER,
            "",
            "Home",
            "",
            "1. My Workspaces",
            "2. Settings",
            "3. About",
            "",
            _HOME_DIVIDER,
            "",
            FOOTER_TEXT,
        ]
    )


def workspaces(items: list[WorkspaceNavigationItem]) -> str:
    lines = ["My Workspaces", ""]
    if items:
        lines.extend(f"{index}. {item.name} — {item.panel}" for index, item in enumerate(items, start=1))
    else:
        lines.append("No workspaces yet. Choose Add Workspace to begin.")
    return "\n".join(lines)


def dashboard(workspace: WorkspaceNavigationItem) -> str:
    status = WorkspaceApplicationService.status_label(workspace.status)
    return f"{workspace.name}\n\nPanel: {workspace.panel}\nStatus: {status}"


def settings() -> str:
    return (
        "Settings\n\n"
        "Manage Telegram and workspace credentials.\n\n"
        "1. Reset Workspace Tokens\n"
        "2. Change Bot Token\n"
        "3. Change Owner IDs"
    )


def about() -> str:
    return f"About\n\nPlatform: {APP_NAME}\nVersion: v{VERSION}\nDeveloper: {DEVELOPER}\nGitHub: {GITHUB_URL}"


def coming_next_phase() -> str:
    return "Coming in the next phase."


def status_label(status: ConnectionStatus) -> str:
    return WorkspaceApplicationService.status_label(status)


def backup_status(latest, *, workspace: str) -> str:
    """Render the Backup page status, mirroring the CLI's latest-backup panel."""
    header = f"Backup — {workspace}"
    if latest is None:
        return f"{header}\n\nLatest Backup: No backup available.\nUsers: —\nArchive Size: —"
    return (
        f"{header}\n\n"
        f"Latest Backup: {relative_time(latest.created_at)}\n"
        f"({latest.created_at:%Y-%m-%d %H:%M:%S})\n"
        f"Users: {latest.users}\n"
        f"Archive Size: {format_size(latest.size_bytes)}"
    )


def backup_progress(stage: str) -> str:
    return f"Backup\n\n{stage}"


def delete_menu() -> str:
    return "Delete Backup\n\n1. Delete Single Backup\n2. Delete All Backups"


def backup_result(summary: BackupSummary) -> str:
    return (
        "Backup completed successfully.\n\n"
        f"Workspace: {summary.workspace}\n"
        f"Users: {summary.users}\n"
        f"Archive Size: {format_size(summary.size_bytes)}\n"
        f"Duration: {format_duration(summary.duration_seconds)}\n"
        f"Latest Backup: {summary.created_at:%Y-%m-%d %H:%M:%S}\n"
        f"Archive Name: {summary.archive_name}"
    )


def backup_history(
    archives: list[BackupArchive],
    *,
    title: str = "Backup History",
    selectable: bool = False,
) -> str:
    lines = [title, ""]
    if not archives:
        lines.append("No backups have been created yet.")
    else:
        lines.extend(f"{index}. {' — '.join(archive_display(archive))}" for index, archive in enumerate(archives, start=1))
        if selectable:
            lines.append("")
            lines.append("Select an archive to view details.")
    return "\n".join(lines)


def archive_details(workspace: str, archive: BackupArchive) -> str:
    name, created, size = archive_display(archive)
    lines = [
        "Archive Details",
        "",
        f"Workspace: {workspace}",
        f"Archive Name: {name}",
        f"Created Time: {created}",
        f"({archive.created_at:%Y-%m-%d %H:%M:%S})",
        f"Archive Size: {size}",
    ]
    if archive.users is not None:
        lines.append(f"User Count: {archive.users}")
    return "\n".join(lines)


def delete_single_confirmation(workspace: str, archive: BackupArchive) -> str:
    name, created, size = archive_display(archive)
    return f"Delete this backup?\n\nWorkspace: {workspace}\nArchive: {name}\nCreated: {created}\nSize: {size}\n\nThis action cannot be undone."


def delete_all_confirmation(workspace: str) -> str:
    return f"Delete ALL backups?\n\nWorkspace: {workspace}\n\nThis action cannot be undone."


def backup_error(detail: str | None = None) -> str:
    base = "Backup could not be completed."
    return f"{base}\n\n{detail}" if detail else f"{base} Please try again."


def no_backups_to_delete() -> str:
    return "No backup files to delete."


def friendly_error() -> str:
    return "Something went wrong. Please try again."


def group_checker_menu(workspace: str, *, selected_count: int = 0, backup_name: str | None = None) -> str:
    if selected_count:
        suffix = f" from {backup_name}" if backup_name else ""
        selection = f"Selected users: {selected_count}{suffix}"
    else:
        selection = "Selected users: none"
    return (
        f"Group Engine — {workspace}\n\n"
        "Central home for all group operations.\n"
        "Write ops share one session: Select Users → Operation → Preview → Confirm → Execute.\n\n"
        f"{selection}\n\n"
        "1. Check\n"
        "2. Select Users\n"
        "3. Add\n"
        "4. Remove\n"
        "5. Replace\n"
        "6. History"
    )


def group_checker_coming_soon(operation: str, *, description: str | None = None) -> str:
    descriptions = {
        "add": (
            "Add groups to selected users.\n"
            "Will follow Select → Preview → Confirmation → Execute → Summary."
        ),
        "remove": (
            "Remove groups from selected users.\n"
            "Will follow Select → Preview → Confirmation → Execute → Summary."
        ),
        "replace": (
            "Replace group membership for selected users.\n"
            "Will follow Select → Preview → Confirmation → Execute → Summary."
        ),
        "history": "Review metadata for past group operations in this workspace.",
    }
    title = operation.capitalize()
    body = description or descriptions.get(operation, "This operation is not available yet.")
    return f"{title}\n\n{body}\n\nStatus: Coming soon\nUses the shared Group Engine workflow when implemented."


def group_engine_select_users(selected_count: int) -> str:
    return (
        "Select Users\n\n"
        "Selection persists until you leave Group Engine.\n"
        f"Currently selected: {selected_count}\n\n"
        "1. Select from backup\n"
        "2. Clear selection"
    )


def group_engine_select_backup(sources: list[BackupSource]) -> str:
    lines = ["Select Backup", ""]
    for index, source in enumerate(sources, start=1):
        lines.append(f"{index}. {source.name} — {source.users} users · {source.size_label}")
    return "\n".join(lines)


def group_engine_backup_mode(backup_name: str, users: int) -> str:
    return (
        f"Select Users\n\n"
        f"Backup: {backup_name}\n"
        f"Users in backup: {users}\n\n"
        "1. Select all users\n"
        "2. Enter usernames"
    )


def group_engine_ask_usernames(backup_name: str) -> str:
    return (
        f"Select Users\n\n"
        f"Backup: {backup_name}\n\n"
        "Send usernames as a message.\n"
        "Example: alice, bob"
    )


def group_engine_selection_result(count: int) -> str:
    return f"Selected {count} user(s)."


def group_engine_error(detail: str) -> str:
    return f"Group Engine\n\n{detail}"


def group_checker_no_backups() -> str:
    return "No backups have been created yet.\nCreate a backup first."


def group_checker_select_backup(sources: list[BackupSource]) -> str:
    lines = ["Select Backup", ""]
    for index, source in enumerate(sources, start=1):
        lines.append(f"{index}. {source.name} — {source.users} users · {source.size_label}")
    return "\n".join(lines)


def group_checker_select_query(backup_name: str) -> str:
    return f"Select Query\n\nBackup: {backup_name}\n\n1. Required Groups"


def group_checker_ask_group_ids(backup_name: str) -> str:
    return (
        f"Required Groups\n\n"
        f"Backup: {backup_name}\n\n"
        "Send the required group IDs as a message.\n"
        "Example: 1, 3"
    )


def group_checker_confirmation(
    workspace: str, backup_name: str, group_ids: tuple[int, ...], users: int
) -> str:
    return (
        "Query Confirmation\n\n"
        f"Workspace: {workspace}\n"
        f"Backup: {backup_name}\n"
        f"Query: Required Groups\n"
        f"Required Groups: {format_group_ids(group_ids)}\n"
        f"Users in Backup: {users}"
    )


def group_checker_progress(stage: str) -> str:
    return f"Group Engine — Check\n\n{stage}"


def group_checker_result(result: GroupCheckerResult, *, limit: int = 30) -> str:
    lines = [
        "Query completed.",
        "",
        f"Backup: {result.backup_name}",
        f"Query: {result.query_label}",
        f"Required Groups: {format_group_ids(result.required_group_ids)}",
        f"Total Users: {result.total_users}",
        f"Matching Users: {result.matching_users}",
        f"Duration: {format_duration(result.duration_seconds)}",
        "",
    ]
    if not result.users:
        lines.append("No users matched this query.")
        return "\n".join(lines)

    lines.append("Username | Current | Missing")
    for row in result.users[:limit]:
        lines.append(
            f"{row.username} | {format_group_ids(row.current_group_ids)} | "
            f"{format_group_ids(row.missing_group_ids)}"
        )
    if result.matching_users > limit:
        lines.append("")
        lines.append(f"Showing first {limit} of {result.matching_users} matching users.")
    return "\n".join(lines)


def group_checker_error(detail: str | None = None) -> str:
    base = "Group Engine could not complete the check."
    return f"{base}\n\n{detail}" if detail else f"{base} Please try again."


def group_checker_invalid_ids(detail: str) -> str:
    return f"Invalid group IDs.\n\n{detail}\n\nSend the required group IDs again (e.g. 1, 3)."


def ask_workspace_name(*, current: str | None = None) -> str:
    if current:
        return f"Edit Workspace\n\nCurrent name: {current}\n\nSend the new workspace name."
    return "Add Workspace\n\nSend the workspace name."


def ask_panel_url(*, current: str | None = None) -> str:
    hint = f"\nCurrent URL: {current}" if current else ""
    return f"Panel URL{hint}\n\nSend the panel base URL (https://…)."


def ask_username(*, current: str | None = None) -> str:
    hint = f"\nCurrent username: {current}" if current else ""
    return f"Username{hint}\n\nSend the panel username."


def ask_password(*, keep_allowed: bool = False) -> str:
    note = "\nSend a dash (-) to keep the current password." if keep_allowed else ""
    return f"Password{note}\n\nSend the panel password."


def ask_token(*, keep_allowed: bool = False) -> str:
    note = "\nSend a dash (-) to keep the current token." if keep_allowed else ""
    return f"Bearer Token{note}\n\nSend the panel bearer token."


def select_integration() -> str:
    return "Select Integration\n\nChoose the panel technology for this workspace."


def select_auth_method() -> str:
    return "Authentication Method\n\n1. Username / Password\n2. Bearer Token"


def select_verify_ssl(*, current: bool | None = None) -> str:
    hint = ""
    if current is not None:
        hint = f"\nCurrent: {'Yes' if current else 'No'}"
    return f"Verify TLS Certificate?{hint}"


def workspace_confirmation(draft: dict, *, title: str = "Create Workspace") -> str:
    auth = draft.get("auth", "password")
    auth_label = "Username / Password" if auth == "password" else "Bearer Token"
    lines = [
        title,
        "",
        f"Name: {draft.get('name', '—')}",
        f"Integration: {draft.get('integration_label', draft.get('integration', '—'))}",
        f"URL: {draft.get('base_url', '—')}",
        f"Authentication: {auth_label}",
    ]
    if auth == "password":
        lines.append(f"Username: {draft.get('username') or '—'}")
        lines.append(f"Password: {'••••••' if draft.get('password') else '—'}")
    else:
        lines.append(f"Token: {'••••••' if draft.get('token') else '—'}")
    lines.append(f"Verify SSL: {'Yes' if draft.get('verify_ssl', True) else 'No'}")
    if "probe_ok" in draft:
        lines.append("")
        lines.append("Connection: 🟢 Connected" if draft["probe_ok"] else "Connection: 🔴 Offline")
    return "\n".join(lines)


def workspace_created(name: str) -> str:
    return f"Workspace '{name}' created successfully."


def workspace_updated(name: str) -> str:
    return f"Workspace '{name}' updated successfully."


def workspace_deleted(name: str) -> str:
    return f"Workspace '{name}' deleted successfully."


def delete_workspace_confirmation(name: str) -> str:
    return (
        f"Delete Workspace\n\n"
        f"Workspace: {name}\n\n"
        "This action cannot be undone.\n\n"
        "Are you sure?"
    )


def workspace_error(detail: str) -> str:
    return f"Workspace operation failed.\n\n{detail}"


def reset_tokens_confirmation() -> str:
    return (
        "Reset Workspace Tokens\n\n"
        "This will remove all saved workspace tokens.\n\n"
        "Workspace configuration,\n"
        "passwords,\n"
        "backups\n"
        "and history\n"
        "will remain.\n\n"
        "Continue?"
    )


def reset_tokens_success(count: int) -> str:
    return "Workspace tokens removed successfully."


def change_bot_token_confirmation() -> str:
    return (
        "Change Bot Token\n\n"
        "You will be asked for a new BOT_TOKEN.\n"
        "Restart the bot after saving to apply the change.\n\n"
        "Continue?"
    )


def ask_bot_token() -> str:
    return "Change Bot Token\n\nSend the new Telegram bot token from @BotFather."


def bot_token_updated() -> str:
    return "Bot token updated successfully.\n\nRestart the bot to apply the changes."


def change_owner_ids_confirmation() -> str:
    return (
        "Change Owner IDs\n\n"
        "You will be asked for one or more Telegram owner IDs.\n"
        "Restart the bot after saving to apply the change.\n\n"
        "Continue?"
    )


def ask_owner_ids() -> str:
    return (
        "Change Owner IDs\n\n"
        "Send one or more numeric Telegram user IDs.\n"
        "Example: 123456789\n"
        "Or: 123456789,987654321"
    )


def owner_ids_updated(owner_ids: list[int]) -> str:
    joined = ", ".join(str(value) for value in owner_ids)
    return f"Owner IDs updated successfully.\n\nOwner IDs: {joined}\n\nRestart the bot to apply the changes."


def settings_error(detail: str) -> str:
    return f"Settings update failed.\n\n{detail}"


def verifying_connection() -> str:
    return "Verifying connection…"
