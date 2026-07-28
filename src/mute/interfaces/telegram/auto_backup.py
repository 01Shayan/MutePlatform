"""Periodic Auto Backup runner hosted by the Telegram bot process.

Each enabled workspace uses its own interval. Due workspaces call the same
``BackupApplicationService.create_export`` pipeline as Manual Backup, then the
archive is delivered to configured Telegram owners.
"""

from __future__ import annotations

import asyncio
import io

from telegram import InputFile

from ...core.logging import get_logger, use_workspace
from ...services.backup import BackupApplicationService, BackupOperationError
from ...services.workspace import ConnectionStatus, WorkspaceApplicationService
from .auth import OwnerAuthorization

logger = get_logger("telegram")

# Check once per minute — per-workspace intervals are evaluated against latest backup age.
_AUTO_BACKUP_TICK_SECONDS = 60


async def start_auto_backup_loop(application) -> None:
    """``post_init`` hook — schedules the Auto Backup tick loop."""
    application.create_task(_auto_backup_loop(application), name="mute-auto-backup")


async def _auto_backup_loop(application) -> None:
    # Brief delay so polling is up before the first tick.
    await asyncio.sleep(5)
    while True:
        try:
            await _run_due_auto_backups(application)
        except asyncio.CancelledError:
            raise
        except Exception:  # noqa: BLE001 — never kill the bot on a scheduler failure
            logger.exception("Auto Backup tick failed")
        await asyncio.sleep(_AUTO_BACKUP_TICK_SECONDS)


async def _run_due_auto_backups(application) -> None:
    workspaces_service: WorkspaceApplicationService | None = application.bot_data.get(
        "telegram_workspace_service"
    )
    authorization: OwnerAuthorization | None = application.bot_data.get("telegram_authorization")
    if workspaces_service is None or authorization is None:
        return

    backup = BackupApplicationService()
    due = backup.due_auto_backup_workspaces(workspaces_service.list())
    if not due:
        return

    for workspace in due:
        use_workspace(workspace.logs_dir)
        logger.info(
            "Auto Backup starting for workspace '%s' (interval=%s min)",
            workspace.name,
            workspace.auto_backup_interval,
        )
        try:
            summary = await asyncio.to_thread(backup.create_export, workspace)
        except BackupOperationError as exc:
            WorkspaceApplicationService.record_connection_status(workspace, ConnectionStatus.OFFLINE)
            logger.warning("Auto Backup failed for '%s': %s", workspace.name, exc)
            continue
        except Exception:  # noqa: BLE001
            WorkspaceApplicationService.record_connection_status(workspace, ConnectionStatus.OFFLINE)
            logger.exception("Auto Backup unexpected error for '%s'", workspace.name)
            continue

        WorkspaceApplicationService.record_connection_status(workspace, ConnectionStatus.CONNECTED)
        download = backup.download_archive(workspace, summary.archive_name)
        if download is None:
            continue
        for owner_id in authorization.owner_ids:
            try:
                await application.bot.send_document(
                    chat_id=owner_id,
                    document=InputFile(io.BytesIO(download.content), filename=download.filename),
                )
            except Exception:  # noqa: BLE001
                logger.exception(
                    "Auto Backup could not send '%s' to owner %s",
                    summary.archive_name,
                    owner_id,
                )
        logger.info(
            "Auto Backup completed for '%s' → %s",
            workspace.name,
            summary.archive_name,
        )
