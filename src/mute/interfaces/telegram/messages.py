"""Shared Telegram message templates."""

from __future__ import annotations

from ...core.constants import APP_NAME
from ...core.constants import DEVELOPER, GITHUB_URL, VERSION
from ...core.timefmt import relative_time
from ...services.workspace import WorkspaceNavigationItem
from ...services.backup import BackupArchive, BackupSummary, archive_display, format_duration, format_size


def home() -> str:
    return "Home\n\n1. My Workspaces\n2. Settings\n3. About"


def workspaces(items: list[WorkspaceNavigationItem]) -> str:
    lines = ["My Workspaces", ""]
    if items:
        lines.extend(f"{index}. {item.name} — {item.panel}" for index, item in enumerate(items, start=1))
    else:
        lines.append("No workspaces yet. Choose Add Workspace to begin.")
    return "\n".join(lines)


def dashboard(workspace: WorkspaceNavigationItem) -> str:
    return f"{workspace.name}\n\nPanel: {workspace.panel}\nStatus: Not checked"


def settings() -> str:
    return "Settings\n\nApplication preferences.\nManage interface and future configuration.\n\nAppearance: Coming soon\nLanguage: Coming soon\nLogging: Coming soon\nBackup: Coming soon\nAdvanced: Coming soon"


def about() -> str:
    return f"About\n\nPlatform: {APP_NAME}\nVersion: v{VERSION}\nDeveloper: {DEVELOPER}\nGitHub: {GITHUB_URL}"


def coming_next_phase() -> str:
    return "Coming in the next phase."


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


def backup_history(archives: list[BackupArchive], *, title: str = "Backup History") -> str:
    lines = [title, ""]
    if not archives:
        lines.append("No backups have been created yet.")
    else:
        lines.extend(f"{index}. {' — '.join(archive_display(archive))}" for index, archive in enumerate(archives, start=1))
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
