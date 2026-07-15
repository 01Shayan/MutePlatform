"""Settings application service tests."""

from __future__ import annotations

import json

import pytest

from mute.core import config
from mute.services.settings import SettingsApplicationService, SettingsOperationError


@pytest.fixture(autouse=True)
def _isolate_config(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "CONFIG_DIR", tmp_path / "config")
    monkeypatch.setattr(config, "SETTINGS_PATH", tmp_path / "config" / "settings.json")
    monkeypatch.setattr(config, "ENV_PATH", tmp_path / ".env")
    config.ensure_settings()


def test_update_bot_token_validates_and_saves():
    service = SettingsApplicationService()
    with pytest.raises(SettingsOperationError, match="empty"):
        service.update_bot_token("  ")
    with pytest.raises(SettingsOperationError, match="invalid"):
        service.update_bot_token("notoken")
    service.update_bot_token("123456:ABC-DEF")
    assert "BOT_TOKEN=123456:ABC-DEF" in config.ENV_PATH.read_text(encoding="utf-8")


def test_parse_and_update_owner_ids():
    service = SettingsApplicationService()
    assert service.parse_owner_ids("123456789") == [123456789]
    assert service.parse_owner_ids("123456789,987654321") == [123456789, 987654321]
    assert service.parse_owner_ids("1 2 1") == [1, 2]
    assert service.parse_owner_ids("1,abc") == []
    with pytest.raises(SettingsOperationError, match="at least one"):
        service.update_owner_ids("bad")
    ids = service.update_owner_ids("10,20")
    assert ids == [10, 20]
    data = json.loads(config.SETTINGS_PATH.read_text(encoding="utf-8"))
    assert data["telegram"]["owner_ids"] == [10, 20]
