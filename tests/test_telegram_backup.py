import asyncio
import json
from datetime import datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

pytest.importorskip("telegram")

from mute.core.workspace import Workspace
from mute.services.workspace import ConnectionStatus
from mute.interfaces.telegram.auth import OwnerAuthorization
from mute.interfaces.telegram.handlers import backup as backup_handler_module
from mute.interfaces.telegram.handlers.backup import make_backup_handler
from mute.interfaces.telegram.router import Router
from mute.interfaces.telegram.session import Screen, SessionManager
from mute.services.backup import BackupApplicationService, BackupSummary

CHAT_ID = 42
OWNER_ID = 1


class FakeWorkspaceService:
    """Returns real Workspace objects so the handler drives the real BackupApplicationService."""

    def __init__(self, workspace: Workspace):
        self._workspace = workspace

    def workspace(self, name):
        return self._workspace if name == self._workspace.name else None

    def navigation_item(self, name):
        return SimpleNamespace(name=name, panel="PasarGuard", status=ConnectionStatus.UNKNOWN)


def _make_workspace(tmp_path) -> Workspace:
    ws = Workspace(name="Prod", integration="pasarguard", base_url="https://panel", root=tmp_path)
    ws.ensure_dirs()
    return ws


def _write_archive(ws: Workspace, created_at: datetime, users: int = 3):
    payload = {
        "metadata": {"created_at": created_at.isoformat(timespec="seconds"), "users_count": users},
        "users": [{"id": i} for i in range(users)],
    }
    directory = ws.backups_dir / created_at.strftime("%Y") / created_at.strftime("%m")
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"backup_{created_at.strftime('%Y-%m-%d_%H-%M-%S')}.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def _write_latest(ws: Workspace, created_at: datetime, users: int = 3):
    payload = {
        "metadata": {"created_at": created_at.isoformat(timespec="seconds"), "users_count": users},
        "users": [{"id": i} for i in range(users)],
    }
    (ws.backups_dir / "backup_latest.json").write_text(json.dumps(payload), encoding="utf-8")


def _make_context():
    bot = SimpleNamespace(
        edit_message_text=AsyncMock(),
        send_document=AsyncMock(),
        delete_message=AsyncMock(),
    )
    return SimpleNamespace(bot=bot)


def _make_update(data: str):
    query = SimpleNamespace(
        data=data,
        answer=AsyncMock(),
        edit_message_text=AsyncMock(),
        message=SimpleNamespace(message_id=555),
    )
    update = SimpleNamespace(
        effective_user=SimpleNamespace(id=OWNER_ID),
        effective_chat=SimpleNamespace(id=CHAT_ID),
        callback_query=query,
    )
    return update, query


def _dispatch(tmp_path, data, *, workspace=None, context=None):
    ws = workspace or _make_workspace(tmp_path)
    sessions = SessionManager()
    sessions.get(CHAT_ID).current_workspace = ws.name
    router = Router(sessions)
    handler = make_backup_handler(OwnerAuthorization(frozenset({OWNER_ID})), router, FakeWorkspaceService(ws))
    update, query = _make_update(data)
    context = context or _make_context()
    asyncio.run(handler(update, context))
    return SimpleNamespace(ws=ws, sessions=sessions, router=router, query=query, context=context)


# -- authorization & guards -----------------------------------------------------------


def test_unauthorized_backup_callback_is_ignored(tmp_path):
    ws = _make_workspace(tmp_path)
    sessions = SessionManager()
    sessions.get(CHAT_ID).current_workspace = ws.name
    handler = make_backup_handler(OwnerAuthorization(frozenset({OWNER_ID})), Router(sessions), FakeWorkspaceService(ws))
    update, query = _make_update("backup:menu")
    update.effective_user = SimpleNamespace(id=999)

    asyncio.run(handler(update, _make_context()))

    query.answer.assert_not_awaited()


def test_missing_workspace_shows_alert(tmp_path):
    sessions = SessionManager()  # no current_workspace set
    handler = make_backup_handler(
        OwnerAuthorization(frozenset({OWNER_ID})), Router(sessions), FakeWorkspaceService(_make_workspace(tmp_path))
    )
    update, query = _make_update("backup:menu")

    asyncio.run(handler(update, _make_context()))

    query.answer.assert_awaited_once()
    assert query.answer.await_args.kwargs.get("show_alert") is True


# -- backup menu / status -------------------------------------------------------------


def test_menu_without_backup_reports_none(tmp_path):
    result = _dispatch(tmp_path, "backup:menu")

    assert result.sessions.get(CHAT_ID).current_screen is Screen.BACKUP
    text = result.query.edit_message_text.await_args.args[0]
    assert "No backup available." in text


def test_menu_with_backup_shows_status(tmp_path):
    ws = _make_workspace(tmp_path)
    _write_latest(ws, datetime.now() - timedelta(hours=2), users=7)

    result = _dispatch(tmp_path, "backup:menu", workspace=ws)

    text = result.query.edit_message_text.await_args.args[0]
    assert "Users: 7" in text
    assert "hours ago" in text


# -- history + archive details --------------------------------------------------------


def test_history_lists_archives(tmp_path):
    ws = _make_workspace(tmp_path)
    _write_archive(ws, datetime(2026, 7, 10, 12, 0, 0))
    _write_archive(ws, datetime(2026, 7, 11, 12, 0, 0))

    result = _dispatch(tmp_path, "backup:history", workspace=ws)

    assert result.sessions.get(CHAT_ID).current_screen is Screen.BACKUP_HISTORY
    text = result.query.edit_message_text.await_args.args[0]
    assert "backup_2026-07-11_12-00-00.json" in text
    assert "backup_2026-07-10_12-00-00.json" in text
    assert "Select an archive" in text
    markup = result.query.edit_message_text.await_args.kwargs["reply_markup"]
    labels = [btn.text for row in markup.inline_keyboard for btn in row]
    assert "backup_2026-07-11_12-00-00.json" in labels
    assert "🏠 Back" in labels


def test_select_archive_opens_details(tmp_path):
    ws = _make_workspace(tmp_path)
    path = _write_archive(ws, datetime(2026, 7, 11, 12, 0, 0), users=5)
    result = _dispatch(tmp_path, f"backup:archive:{path.name}", workspace=ws)

    assert result.sessions.get(CHAT_ID).current_screen is Screen.BACKUP_ARCHIVE_DETAIL
    assert result.sessions.get(CHAT_ID).current_action == path.name
    text = result.query.edit_message_text.await_args.args[0]
    assert "Archive Details" in text
    assert path.name in text
    assert "User Count: 5" in text
    assert "Archive Size:" in text
    markup = result.query.edit_message_text.await_args.kwargs["reply_markup"]
    labels = [btn.text for row in markup.inline_keyboard for btn in row]
    assert labels == ["⬇ Download Backup", "❌ Delete Backup", "🏠 Back"]
    callbacks = [btn.callback_data for row in markup.inline_keyboard for btn in row]
    assert callbacks == [
        f"backup:download:{path.name}",
        f"backup:delete:{path.name}",
        "backup:history",
    ]


def test_archive_details_back_returns_to_history(tmp_path):
    ws = _make_workspace(tmp_path)
    path = _write_archive(ws, datetime(2026, 7, 11, 12, 0, 0))
    sessions = SessionManager()
    sessions.get(CHAT_ID).current_workspace = ws.name
    router = Router(sessions)
    handler = make_backup_handler(OwnerAuthorization(frozenset({OWNER_ID})), router, FakeWorkspaceService(ws))
    context = _make_context()

    update, query = _make_update(f"backup:archive:{path.name}")
    asyncio.run(handler(update, context))
    assert sessions.get(CHAT_ID).current_screen is Screen.BACKUP_ARCHIVE_DETAIL

    query.data = "backup:history"
    asyncio.run(handler(update, context))
    assert sessions.get(CHAT_ID).current_screen is Screen.BACKUP_HISTORY
    assert "Backup History" in query.edit_message_text.await_args.args[0]


def test_download_from_details_stays_on_details(tmp_path):
    ws = _make_workspace(tmp_path)
    path = _write_archive(ws, datetime(2026, 7, 11, 12, 0, 0), users=2)
    sessions = SessionManager()
    sessions.get(CHAT_ID).current_workspace = ws.name
    router = Router(sessions)
    handler = make_backup_handler(OwnerAuthorization(frozenset({OWNER_ID})), router, FakeWorkspaceService(ws))
    context = _make_context()

    update, query = _make_update(f"backup:archive:{path.name}")
    asyncio.run(handler(update, context))

    query.data = f"backup:download:{path.name}"
    asyncio.run(handler(update, context))

    context.bot.send_document.assert_awaited()
    assert sessions.get(CHAT_ID).current_screen is Screen.BACKUP_ARCHIVE_DETAIL
    text = query.edit_message_text.await_args.args[0]
    assert "Archive Details" in text
    assert path.name in text


def test_delete_from_details_confirm_no_returns_to_details(tmp_path):
    ws = _make_workspace(tmp_path)
    path = _write_archive(ws, datetime(2026, 7, 11, 12, 0, 0))
    sessions = SessionManager()
    sessions.get(CHAT_ID).current_workspace = ws.name
    router = Router(sessions)
    handler = make_backup_handler(OwnerAuthorization(frozenset({OWNER_ID})), router, FakeWorkspaceService(ws))

    update, query = _make_update(f"backup:archive:{path.name}")
    asyncio.run(handler(update, _make_context()))

    query.data = f"backup:delete:{path.name}"
    asyncio.run(handler(update, _make_context()))
    assert sessions.get(CHAT_ID).current_screen is Screen.BACKUP_DELETE_CONFIRM
    markup = query.edit_message_text.await_args.kwargs["reply_markup"]
    no_callback = markup.inline_keyboard[0][1].callback_data
    assert no_callback == f"backup:archive:{path.name}"

    query.data = no_callback
    asyncio.run(handler(update, _make_context()))
    assert sessions.get(CHAT_ID).current_screen is Screen.BACKUP_ARCHIVE_DETAIL


def test_delete_from_details_yes_returns_to_history(tmp_path):
    ws = _make_workspace(tmp_path)
    path = _write_archive(ws, datetime(2026, 7, 11, 12, 0, 0))
    sessions = SessionManager()
    sessions.get(CHAT_ID).current_workspace = ws.name
    router = Router(sessions)
    handler = make_backup_handler(OwnerAuthorization(frozenset({OWNER_ID})), router, FakeWorkspaceService(ws))

    update, query = _make_update(f"backup:archive:{path.name}")
    asyncio.run(handler(update, _make_context()))
    query.data = f"backup:delete:{path.name}"
    asyncio.run(handler(update, _make_context()))
    query.data = f"backup:confirm-delete:{path.name}"
    asyncio.run(handler(update, _make_context()))

    assert not path.exists()
    assert sessions.get(CHAT_ID).current_screen is Screen.BACKUP_HISTORY


# -- delete flows ---------------------------------------------------------------------


def test_delete_single_list_then_confirm_then_delete(tmp_path):
    ws = _make_workspace(tmp_path)
    older = _write_archive(ws, datetime(2026, 7, 10, 12, 0, 0))
    newer = _write_archive(ws, datetime(2026, 7, 11, 12, 0, 0))
    sessions = SessionManager()
    sessions.get(CHAT_ID).current_workspace = ws.name
    router = Router(sessions)
    handler = make_backup_handler(OwnerAuthorization(frozenset({OWNER_ID})), router, FakeWorkspaceService(ws))

    update, query = _make_update("backup:delete-single")
    asyncio.run(handler(update, _make_context()))
    assert sessions.get(CHAT_ID).current_screen is Screen.BACKUP_DELETE_SINGLE

    query.data = f"backup:delete:{newer.name}"
    asyncio.run(handler(update, _make_context()))
    assert sessions.get(CHAT_ID).current_screen is Screen.BACKUP_DELETE_CONFIRM
    confirm_text = query.edit_message_text.await_args.args[0]
    assert newer.name in confirm_text
    assert "cannot be undone" in confirm_text

    query.data = f"backup:confirm-delete:{newer.name}"
    asyncio.run(handler(update, _make_context()))
    assert not newer.exists()
    assert older.exists()
    assert sessions.get(CHAT_ID).current_screen is Screen.BACKUP


def test_delete_all_confirmation_and_execution(tmp_path):
    ws = _make_workspace(tmp_path)
    a = _write_archive(ws, datetime(2026, 7, 10, 12, 0, 0))
    b = _write_archive(ws, datetime(2026, 7, 11, 12, 0, 0))
    _write_latest(ws, datetime(2026, 7, 11, 12, 0, 0))
    sessions = SessionManager()
    sessions.get(CHAT_ID).current_workspace = ws.name
    router = Router(sessions)
    handler = make_backup_handler(OwnerAuthorization(frozenset({OWNER_ID})), router, FakeWorkspaceService(ws))

    update, query = _make_update("backup:delete-all")
    asyncio.run(handler(update, _make_context()))
    assert sessions.get(CHAT_ID).current_screen is Screen.BACKUP_DELETE_ALL_CONFIRM

    query.data = "backup:confirm-delete-all"
    asyncio.run(handler(update, _make_context()))
    assert not a.exists() and not b.exists()
    assert BackupApplicationService().archives(ws) == []
    assert ws.backups_dir.exists()  # directory is kept
    assert sessions.get(CHAT_ID).current_screen is Screen.BACKUP


def test_delete_single_with_no_backups_returns_to_delete_menu(tmp_path):
    result = _dispatch(tmp_path, "backup:delete-single")

    text = result.query.edit_message_text.await_args.args[0]
    assert "No backup files to delete." in text


# -- download -------------------------------------------------------------------------


def test_download_sends_existing_archive_bytes(tmp_path):
    ws = _make_workspace(tmp_path)
    archive = _write_archive(ws, datetime(2026, 7, 11, 12, 0, 0))
    context = _make_context()

    result = _dispatch(tmp_path, f"backup:download:{archive.name}", workspace=ws, context=context)

    context.bot.send_document.assert_awaited_once()
    document = context.bot.send_document.await_args.kwargs["document"]
    assert document.filename == archive.name
    # After delivery the message returns to the refreshed Backup page.
    result.query.edit_message_text.assert_awaited()


def test_download_missing_archive_alerts(tmp_path):
    context = _make_context()
    result = _dispatch(tmp_path, "backup:download:backup_missing.json", context=context)

    context.bot.send_document.assert_not_awaited()
    result.query.answer.assert_awaited_once()
    assert result.query.answer.await_args.kwargs.get("show_alert") is True


# -- create export & progress ---------------------------------------------------------


def test_create_export_edits_progress_stages_and_shows_result(tmp_path, monkeypatch):
    ws = _make_workspace(tmp_path)
    summary = BackupSummary(
        workspace=ws.name, users=2, size_bytes=2048, duration_seconds=1.5,
        created_at=datetime(2026, 7, 12, 9, 0, 0), archive_name="backup_2026-07-12_09-00-00.json",
        integration="PasarGuard",
    )

    def fake_create_export(workspace, progress):
        progress("Exporting users", 0, 2)  # Loading users…
        progress("Exporting users", 1, 2)  # deduped (still loading)
        progress("Exporting users", 2, 2)  # Writing backup…
        return summary

    fake_service = SimpleNamespace(
        create_export=fake_create_export,
        download_archive=lambda workspace, name: None,
    )
    monkeypatch.setattr(backup_handler_module, "BackupApplicationService", lambda: fake_service)

    context = _make_context()
    result = _dispatch(tmp_path, "backup:create", workspace=ws, context=context)

    texts = [call.kwargs["text"] for call in context.bot.edit_message_text.await_args_list]
    assert any("Connecting…" in t for t in texts)
    assert any("Loading users" in t for t in texts)
    assert any("Writing backup" in t for t in texts)
    assert any("Backup completed successfully" in t for t in texts)
    # Success screen: Download Backup + Back to workspace dashboard.
    final = context.bot.edit_message_text.await_args_list[-1]
    rows = final.kwargs["reply_markup"].inline_keyboard
    assert rows[0][0].text == "⬇ Download Backup"
    assert rows[0][0].callback_data == f"backup:download:{summary.archive_name}"
    assert rows[1][0].text == "🏠 Back"
    assert rows[1][0].callback_data == "backup:dashboard"
    assert result.sessions.get(CHAT_ID).current_screen is Screen.BACKUP


def test_create_export_failure_shows_error(tmp_path, monkeypatch):
    from mute.services.backup import BackupOperationError

    def fake_create_export(workspace, progress):
        raise BackupOperationError("panel unreachable")

    monkeypatch.setattr(
        backup_handler_module,
        "BackupApplicationService",
        lambda: SimpleNamespace(
            create_export=fake_create_export,
            download_archive=lambda workspace, name: None,
        ),
    )

    context = _make_context()
    _dispatch(tmp_path, "backup:create", context=context)

    texts = [call.kwargs["text"] for call in context.bot.edit_message_text.await_args_list]
    assert any("could not be completed" in t for t in texts)
    assert any("panel unreachable" in t for t in texts)


# -- back navigation ------------------------------------------------------------------


def test_back_from_menu_returns_to_dashboard(tmp_path):
    result = _dispatch(tmp_path, "backup:dashboard")

    assert result.sessions.get(CHAT_ID).current_screen is Screen.DASHBOARD
    assert result.sessions.get(CHAT_ID).current_workspace == result.ws.name
    result.query.edit_message_text.assert_awaited()
    text = result.query.edit_message_text.await_args.args[0]
    assert result.ws.name in text
    markup = result.query.edit_message_text.await_args.kwargs["reply_markup"]
    labels = [btn.text for row in markup.inline_keyboard for btn in row]
    assert "📦 Backup" in labels
    assert "🛠 Bulk Operations" in labels


def test_back_from_success_keyboard_uses_dashboard_callback():
    from mute.interfaces.telegram.keyboards import backup_result_keyboard

    markup = backup_result_keyboard("backup_2026-07-15_12-00-00.json")
    rows = markup.inline_keyboard
    assert rows[0][0].text == "⬇ Download Backup"
    assert rows[0][0].callback_data == "backup:download:backup_2026-07-15_12-00-00.json"
    assert rows[1][0].text == "🏠 Back"
    assert rows[1][0].callback_data == "backup:dashboard"
