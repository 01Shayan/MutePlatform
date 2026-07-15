"""CLI Settings screen — mirrors Telegram Settings via shared services."""

from __future__ import annotations

from mute.cli.screens import settings as screen
from mute.core import config
from mute.core.workspace import WorkspaceStore
from mute.services.workspace import WorkspaceApplicationService


def _point_config(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "CONFIG_DIR", tmp_path / "config")
    monkeypatch.setattr(config, "SETTINGS_PATH", tmp_path / "config" / "settings.json")
    monkeypatch.setattr(config, "ENV_PATH", tmp_path / ".env")
    (tmp_path / "config").mkdir(parents=True, exist_ok=True)
    config.ensure_settings()


def _stub_ui(monkeypatch):
    monkeypatch.setattr(screen.theme, "page", lambda *a, **k: None)
    monkeypatch.setattr(screen.theme, "pause", lambda *a, **k: None)
    monkeypatch.setattr(screen.theme, "notify_success", lambda *a, **k: None)
    monkeypatch.setattr(screen.theme, "notify_info", lambda *a, **k: None)
    monkeypatch.setattr(screen.theme, "notify_error", lambda *a, **k: None)


def test_settings_back_exits(monkeypatch):
    _stub_ui(monkeypatch)
    monkeypatch.setattr(screen.Prompt, "ask", lambda *a, **k: "0")
    screen.show()


def test_reset_tokens_confirmed(tmp_path, monkeypatch):
    _point_config(tmp_path, monkeypatch)
    _stub_ui(monkeypatch)
    store = WorkspaceStore(root=tmp_path / "workspaces", registry_path=tmp_path / "config" / "workspaces.json")
    service = WorkspaceApplicationService(store)
    service.create(
        name="Tok",
        integration="pasarguard",
        connection={"base_url": "https://a", "token": "secret"},
    )
    monkeypatch.setattr(
        WorkspaceApplicationService,
        "for_navigation",
        classmethod(lambda cls: service),
    )
    answers = iter(["1", "1", "0"])
    monkeypatch.setattr(screen.Prompt, "ask", lambda *a, **k: next(answers))
    screen.show()
    assert service.workspace("Tok").token is None


def test_reset_tokens_cancelled(tmp_path, monkeypatch):
    _point_config(tmp_path, monkeypatch)
    _stub_ui(monkeypatch)
    store = WorkspaceStore(root=tmp_path / "workspaces", registry_path=tmp_path / "config" / "workspaces.json")
    service = WorkspaceApplicationService(store)
    service.create(
        name="Tok",
        integration="pasarguard",
        connection={"base_url": "https://a", "token": "secret"},
    )
    monkeypatch.setattr(
        WorkspaceApplicationService,
        "for_navigation",
        classmethod(lambda cls: service),
    )
    answers = iter(["1", "0", "0"])
    monkeypatch.setattr(screen.Prompt, "ask", lambda *a, **k: next(answers))
    screen.show()
    assert service.workspace("Tok").token == "secret"


def test_change_bot_token_success(tmp_path, monkeypatch):
    _point_config(tmp_path, monkeypatch)
    _stub_ui(monkeypatch)
    answers = iter(["2", "1", "123456:CLI-TOKEN", "0"])
    monkeypatch.setattr(screen.Prompt, "ask", lambda *a, **k: next(answers))
    screen.show()
    assert "BOT_TOKEN=123456:CLI-TOKEN" in config.ENV_PATH.read_text(encoding="utf-8")


def test_change_bot_token_invalid(tmp_path, monkeypatch):
    _point_config(tmp_path, monkeypatch)
    _stub_ui(monkeypatch)
    errors = []
    monkeypatch.setattr(screen.theme, "notify_error", lambda msg: errors.append(msg))
    answers = iter(["2", "1", "badtoken", "0"])
    monkeypatch.setattr(screen.Prompt, "ask", lambda *a, **k: next(answers))
    screen.show()
    assert errors
    assert "invalid" in errors[0].lower()


def test_change_owner_ids_success(tmp_path, monkeypatch):
    _point_config(tmp_path, monkeypatch)
    _stub_ui(monkeypatch)
    answers = iter(["3", "1", "111,222", "0"])
    monkeypatch.setattr(screen.Prompt, "ask", lambda *a, **k: next(answers))
    screen.show()
    text = config.SETTINGS_PATH.read_text(encoding="utf-8")
    assert "111" in text and "222" in text
