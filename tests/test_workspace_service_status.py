"""Workspace application service — status cache, token reset, validation."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

from mute.core.workspace import Workspace, WorkspaceStore
from mute.services.workspace import (
    ConnectionStatus,
    WorkspaceApplicationService,
    WorkspaceOperationError,
)


def _store(tmp_path) -> WorkspaceStore:
    return WorkspaceStore(
        root=tmp_path / "workspaces", registry_path=tmp_path / "config" / "workspaces.json"
    )


def _service(tmp_path) -> WorkspaceApplicationService:
    return WorkspaceApplicationService(_store(tmp_path))


def test_connection_status_unknown_when_absent(tmp_path):
    service = _service(tmp_path)
    ws = service.create(
        name="Prod",
        integration="pasarguard",
        connection={"base_url": "https://panel", "username": "a", "password": "b", "verify_ssl": True},
    )
    assert WorkspaceApplicationService.connection_status(ws) is ConnectionStatus.UNKNOWN
    item = service.navigation_item("Prod")
    assert item is not None
    assert item.status is ConnectionStatus.UNKNOWN


def test_record_and_read_connection_status(tmp_path):
    service = _service(tmp_path)
    ws = service.create(
        name="Prod",
        integration="pasarguard",
        connection={"base_url": "https://panel", "username": "a", "password": "b"},
    )
    WorkspaceApplicationService.record_connection_status(ws, ConnectionStatus.CONNECTED)
    assert WorkspaceApplicationService.connection_status(ws) is ConnectionStatus.CONNECTED
    path = ws.cache_dir / "connection_status.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["status"] == "connected"
    assert "checked_at" in payload

    WorkspaceApplicationService.record_connection_status(ws, ConnectionStatus.OFFLINE)
    assert service.navigation_item("Prod").status is ConnectionStatus.OFFLINE


def test_probe_connection_does_not_persist(tmp_path):
    service = _service(tmp_path)
    ws = service.create(
        name="Prod",
        integration="pasarguard",
        connection={"base_url": "https://panel", "username": "a", "password": "b"},
    )
    client = MagicMock()
    client.test_connection.return_value = True
    with patch("mute.services.workspace.service.create_client", return_value=client):
        assert WorkspaceApplicationService.probe_connection(ws) is True
    assert not (ws.cache_dir / "connection_status.json").exists()
    assert WorkspaceApplicationService.connection_status(ws) is ConnectionStatus.UNKNOWN


def test_connection_is_available_persists(tmp_path):
    service = _service(tmp_path)
    ws = service.create(
        name="Prod",
        integration="pasarguard",
        connection={"base_url": "https://panel", "username": "a", "password": "b"},
    )
    client = MagicMock()
    client.test_connection.return_value = True
    with patch("mute.services.workspace.service.create_client", return_value=client):
        assert WorkspaceApplicationService.connection_is_available(ws) is True
    assert WorkspaceApplicationService.connection_status(ws) is ConnectionStatus.CONNECTED

    client.test_connection.side_effect = RuntimeError("down")
    with patch("mute.services.workspace.service.create_client", return_value=client):
        assert WorkspaceApplicationService.connection_is_available(ws) is False
    assert WorkspaceApplicationService.connection_status(ws) is ConnectionStatus.OFFLINE


def test_clear_all_tokens_preserves_passwords_and_urls(tmp_path):
    service = _service(tmp_path)
    with_token = service.create(
        name="TokenWS",
        integration="pasarguard",
        connection={
            "base_url": "https://a",
            "token": "secret-token",
            "verify_ssl": False,
        },
    )
    with_password = service.create(
        name="PassWS",
        integration="pasarguard",
        connection={
            "base_url": "https://b",
            "username": "admin",
            "password": "pw",
            "token": "also-token",
            "verify_ssl": True,
        },
    )
    cleared = service.clear_all_tokens()
    assert cleared == 2
    reloaded_token = service.workspace("TokenWS")
    reloaded_pass = service.workspace("PassWS")
    assert reloaded_token is not None and reloaded_token.token is None
    assert reloaded_token.base_url == "https://a"
    assert reloaded_token.verify_ssl is False
    assert reloaded_pass is not None and reloaded_pass.token is None
    assert reloaded_pass.username == "admin"
    assert reloaded_pass.password == "pw"
    assert reloaded_pass.base_url == "https://b"
    assert service.workspace("TokenWS") is not None
    assert service.workspace("PassWS") is not None
    # Idempotent second call.
    assert service.clear_all_tokens() == 0
    assert with_token.name == "TokenWS"
    assert with_password.name == "PassWS"


def test_validate_name_rejects_collision_and_invalid(tmp_path):
    service = _service(tmp_path)
    service.create(
        name="Prod",
        integration="pasarguard",
        connection={"base_url": "https://panel"},
    )
    with pytest.raises(WorkspaceOperationError, match="already exists"):
        service.validate_name("Prod")
    assert service.validate_name("Prod", current="Prod") == "Prod"
    with pytest.raises(WorkspaceOperationError):
        service.validate_name("bad/name")


def test_corrupt_status_file_yields_unknown(tmp_path):
    service = _service(tmp_path)
    ws = service.create(
        name="Prod",
        integration="pasarguard",
        connection={"base_url": "https://panel"},
    )
    path = ws.cache_dir / "connection_status.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("not-json", encoding="utf-8")
    assert WorkspaceApplicationService.connection_status(ws) is ConnectionStatus.UNKNOWN


def test_initialize_activate_and_for_navigation(tmp_path, monkeypatch):
    service = _service(tmp_path)
    assert service.initialize() is None
    ws = service.create(
        name="Prod",
        integration="pasarguard",
        connection={"base_url": "https://panel"},
    )
    assert service.activate(ws) is True
    assert service.navigation_item("missing") is None
    assert service.initialize() is not None

    monkeypatch.setattr(
        "mute.services.workspace.service.WorkspaceStore",
        lambda: _store(tmp_path),
    )
    nav = WorkspaceApplicationService.for_navigation()
    assert isinstance(nav, WorkspaceApplicationService)


def test_update_rename_failure_returns_none(tmp_path):
    service = _service(tmp_path)
    ws = service.create(
        name="Prod",
        integration="pasarguard",
        connection={"base_url": "https://panel"},
    )
    service.create(
        name="Taken",
        integration="pasarguard",
        connection={"base_url": "https://other"},
    )
    original_rename = service.store.rename

    def fail_rename(old, new):
        if new == "Taken":
            return False
        return original_rename(old, new)

    service.store.rename = fail_rename  # type: ignore[method-assign]
    result = service.update(
        ws,
        name="Taken",
        integration="pasarguard",
        connection={"base_url": "https://panel"},
    )
    assert result is None
