"""Shared connection status cache — CLI and Telegram read the same source of truth."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from mute.cli.screens import dashboard as cli_dashboard
from mute.core.workspace import WorkspaceStore
from mute.interfaces.telegram.messages import dashboard as telegram_dashboard
from mute.services.workspace import ConnectionStatus, WorkspaceApplicationService


def _service(tmp_path) -> WorkspaceApplicationService:
    return WorkspaceApplicationService(
        WorkspaceStore(root=tmp_path / "workspaces", registry_path=tmp_path / "config" / "workspaces.json")
    )


def test_new_workspace_status_is_unknown(tmp_path):
    service = _service(tmp_path)
    service.create(
        name="Fresh",
        integration="pasarguard",
        connection={"base_url": "https://panel", "username": "a", "password": "b"},
    )
    item = service.navigation_item("Fresh")
    assert item.status is ConnectionStatus.UNKNOWN
    assert "Unknown" in WorkspaceApplicationService.status_label(item.status)
    assert "Unknown" in telegram_dashboard(item)


def test_cli_verify_updates_cache_visible_to_telegram(tmp_path, monkeypatch):
    service = _service(tmp_path)
    ws = service.create(
        name="Prod",
        integration="pasarguard",
        connection={"base_url": "https://panel", "username": "a", "password": "b"},
    )
    assert service.navigation_item("Prod").status is ConnectionStatus.UNKNOWN

    client = MagicMock()
    client.test_connection.return_value = True

    class _Status:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

    monkeypatch.setattr(cli_dashboard.console, "status", lambda *a, **k: _Status())
    with patch("mute.services.workspace.service.create_client", return_value=client):
        label = cli_dashboard._verify_and_status_label(ws)

    assert "Connected" in label
    assert "🟢" in label
    # Same cache Telegram navigation reads.
    item = service.navigation_item("Prod")
    assert item.status is ConnectionStatus.CONNECTED
    assert telegram_dashboard(item) == f"Prod\n\nPanel: PasarGuard\nStatus: {label}"


def test_cli_offline_probe_shared_with_telegram(tmp_path, monkeypatch):
    service = _service(tmp_path)
    ws = service.create(
        name="Prod",
        integration="pasarguard",
        connection={"base_url": "https://panel", "username": "a", "password": "b"},
    )
    client = MagicMock()
    client.test_connection.side_effect = RuntimeError("down")

    class _Status:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

    monkeypatch.setattr(cli_dashboard.console, "status", lambda *a, **k: _Status())
    with patch("mute.services.workspace.service.create_client", return_value=client):
        label = cli_dashboard._verify_and_status_label(ws)

    assert "Offline" in label
    item = service.navigation_item("Prod")
    assert item.status is ConnectionStatus.OFFLINE
    assert WorkspaceApplicationService.status_label(item.status) == label
    assert "🔴 Offline" in telegram_dashboard(item)


def test_telegram_record_visible_to_cli_status_label(tmp_path):
    service = _service(tmp_path)
    ws = service.create(
        name="Prod",
        integration="pasarguard",
        connection={"base_url": "https://panel", "token": "t"},
    )
    WorkspaceApplicationService.record_connection_status(ws, ConnectionStatus.CONNECTED)
    assert WorkspaceApplicationService.connection_status(ws) is ConnectionStatus.CONNECTED
    assert "🟢 Connected" == WorkspaceApplicationService.status_label(
        WorkspaceApplicationService.connection_status(ws)
    )


def test_status_labels_are_canonical():
    assert WorkspaceApplicationService.status_label(ConnectionStatus.CONNECTED) == "🟢 Connected"
    assert WorkspaceApplicationService.status_label(ConnectionStatus.OFFLINE) == "🔴 Offline"
    assert WorkspaceApplicationService.status_label(ConnectionStatus.UNKNOWN) == "⚪ Unknown"
