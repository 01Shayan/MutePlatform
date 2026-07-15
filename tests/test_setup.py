import json

from mute.core import config


def _point_config_to(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "CONFIG_DIR", tmp_path / "config")
    monkeypatch.setattr(config, "SETTINGS_PATH", tmp_path / "config" / "settings.json")
    monkeypatch.setattr(config, "ENV_PATH", tmp_path / ".env")


# -- first-run detection --------------------------------------------------------------


def _complete_install(tmp_path, monkeypatch):
    """A fully configured installation: settings.json + .env + token + owner id."""
    _point_config_to(tmp_path, monkeypatch)
    config.save_bot_token("123456:TOKEN")
    config.save_telegram_config(enabled=True, owner_ids=[123456789])


def test_first_run_when_nothing_exists(tmp_path, monkeypatch):
    _point_config_to(tmp_path, monkeypatch)
    assert config.is_first_run() is True


def test_first_run_when_settings_missing(tmp_path, monkeypatch):
    # A valid .env alone is not enough — settings.json must also exist.
    _point_config_to(tmp_path, monkeypatch)
    config.save_bot_token("123456:TOKEN")
    assert not config.SETTINGS_PATH.exists()
    assert config.is_first_run() is True


def test_first_run_when_env_missing(tmp_path, monkeypatch):
    # settings.json with a valid owner id, but no .env at all.
    _point_config_to(tmp_path, monkeypatch)
    config.save_telegram_config(enabled=True, owner_ids=[123456789])
    assert not config.ENV_PATH.exists()
    assert config.is_first_run() is True


def test_first_run_when_bot_token_key_missing(tmp_path, monkeypatch):
    # .env exists but contains no BOT_TOKEN entry.
    _point_config_to(tmp_path, monkeypatch)
    config.save_telegram_config(enabled=True, owner_ids=[123456789])
    config.ENV_PATH.write_text("PASARGUARD_BASE_URL=https://panel\n", encoding="utf-8")
    assert config.is_first_run() is True


def test_first_run_when_bot_token_empty(tmp_path, monkeypatch):
    _point_config_to(tmp_path, monkeypatch)
    config.save_telegram_config(enabled=True, owner_ids=[123456789])
    config.ENV_PATH.write_text("BOT_TOKEN=\n", encoding="utf-8")
    assert config.is_first_run() is True


def test_first_run_when_owner_ids_missing(tmp_path, monkeypatch):
    # settings.json has a telegram section but no owner_ids key.
    _point_config_to(tmp_path, monkeypatch)
    config.CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    config.SETTINGS_PATH.write_text(
        json.dumps({"config_version": config.CONFIG_VERSION, "telegram": {"enabled": True}}),
        encoding="utf-8",
    )
    config.save_bot_token("123456:TOKEN")
    assert config.is_first_run() is True


def test_first_run_when_owner_ids_empty(tmp_path, monkeypatch):
    _point_config_to(tmp_path, monkeypatch)
    config.save_bot_token("123456:TOKEN")
    config.save_telegram_config(enabled=True, owner_ids=[])
    assert config.is_first_run() is True


def test_first_run_when_owner_ids_all_invalid(tmp_path, monkeypatch):
    # Non-numeric owner ids coerce to an empty list → still not configured.
    _point_config_to(tmp_path, monkeypatch)
    config.CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    config.SETTINGS_PATH.write_text(
        json.dumps({"config_version": config.CONFIG_VERSION, "telegram": {"enabled": True, "owner_ids": ["nope"]}}),
        encoding="utf-8",
    )
    config.save_bot_token("123456:TOKEN")
    assert config.is_first_run() is True


def test_not_first_run_when_fully_configured(tmp_path, monkeypatch):
    _complete_install(tmp_path, monkeypatch)
    assert config.is_first_run() is False


def test_not_first_run_when_configured_but_telegram_disabled(tmp_path, monkeypatch):
    # An existing, complete installation with Telegram disabled is still "configured".
    _point_config_to(tmp_path, monkeypatch)
    config.save_bot_token("123456:TOKEN")
    config.save_telegram_config(enabled=False, owner_ids=[123456789])
    assert config.is_first_run() is False


def test_not_first_run_with_quoted_bot_token(tmp_path, monkeypatch):
    _point_config_to(tmp_path, monkeypatch)
    config.save_telegram_config(enabled=True, owner_ids=[1])
    config.ENV_PATH.write_text('BOT_TOKEN="123456:TOKEN"\n', encoding="utf-8")
    assert config.is_first_run() is False


def test_is_first_run_has_no_side_effects(tmp_path, monkeypatch):
    # Detection must never create configuration files.
    _point_config_to(tmp_path, monkeypatch)
    config.is_first_run()
    assert not config.SETTINGS_PATH.exists()
    assert not config.ENV_PATH.exists()


def test_migration_still_works_and_completes_install(tmp_path, monkeypatch):
    # A legacy settings file migrates in place, and with a valid .env the install is complete.
    _point_config_to(tmp_path, monkeypatch)
    config.CONFIG_DIR.mkdir(parents=True)
    config.SETTINGS_PATH.write_text(
        json.dumps({"appearance": "x", "telegram": {"enabled": True, "owner_ids": [5], "config_version": 1}}),
        encoding="utf-8",
    )
    config.save_bot_token("123456:TOKEN")

    config.ensure_settings()

    data = json.loads(config.SETTINGS_PATH.read_text(encoding="utf-8"))
    assert data == {"config_version": config.CONFIG_VERSION, "telegram": {"enabled": True, "owner_ids": [5]}}
    assert config.is_first_run() is False


# -- migration ------------------------------------------------------------------------


def test_migrate_v1_moves_config_version_and_drops_placeholders():
    old = {
        "appearance": "default",
        "language": "en",
        "logging": "info",
        "backup": {},
        "advanced": {},
        "telegram": {"enabled": True, "owner_ids": [111, 222], "config_version": 1},
    }

    clean, changed = config.migrate_settings(old)

    assert changed is True
    assert clean == {
        "config_version": config.CONFIG_VERSION,
        "telegram": {"enabled": True, "owner_ids": [111, 222]},
    }
    # legacy / placeholder keys are gone; config_version is top-level
    assert "appearance" not in clean
    assert "config_version" not in clean["telegram"]


def test_migrate_is_idempotent_on_current_schema():
    current = {"config_version": config.CONFIG_VERSION, "telegram": {"enabled": False, "owner_ids": []}}
    clean, changed = config.migrate_settings(current)
    assert changed is False
    assert clean == current


def test_migrate_handles_missing_telegram_section():
    clean, changed = config.migrate_settings({"appearance": "default"})
    assert changed is True
    assert clean == {"config_version": config.CONFIG_VERSION, "telegram": {"enabled": False, "owner_ids": []}}


def test_migrate_coerces_owner_ids_to_ints():
    clean, _ = config.migrate_settings({"telegram": {"owner_ids": ["7", 8, "bad"]}})
    assert clean["telegram"]["owner_ids"] == [7, 8]


# -- ensure_settings ------------------------------------------------------------------


def test_ensure_settings_creates_default_when_missing(tmp_path, monkeypatch):
    _point_config_to(tmp_path, monkeypatch)
    config.ensure_settings()
    data = json.loads(config.SETTINGS_PATH.read_text(encoding="utf-8"))
    assert data == {"config_version": config.CONFIG_VERSION, "telegram": {"enabled": False, "owner_ids": []}}


def test_ensure_settings_migrates_existing_file(tmp_path, monkeypatch):
    _point_config_to(tmp_path, monkeypatch)
    config.CONFIG_DIR.mkdir(parents=True)
    config.SETTINGS_PATH.write_text(
        json.dumps({"appearance": "x", "telegram": {"enabled": True, "owner_ids": [5], "config_version": 1}}),
        encoding="utf-8",
    )

    config.ensure_settings()

    data = json.loads(config.SETTINGS_PATH.read_text(encoding="utf-8"))
    assert data == {"config_version": config.CONFIG_VERSION, "telegram": {"enabled": True, "owner_ids": [5]}}


# -- secrets in .env only -------------------------------------------------------------


def test_save_bot_token_writes_env_only(tmp_path, monkeypatch):
    _point_config_to(tmp_path, monkeypatch)
    config.save_bot_token("123456:SECRET")

    assert config.ENV_PATH.read_text(encoding="utf-8").strip() == "BOT_TOKEN=123456:SECRET"


def test_save_bot_token_preserves_other_env_vars(tmp_path, monkeypatch):
    _point_config_to(tmp_path, monkeypatch)
    config.ENV_PATH.write_text("PASARGUARD_BASE_URL=https://panel\nBOT_TOKEN=old\n", encoding="utf-8")

    config.save_bot_token("new-token")

    text = config.ENV_PATH.read_text(encoding="utf-8")
    assert "PASARGUARD_BASE_URL=https://panel" in text
    assert "BOT_TOKEN=new-token" in text
    assert "BOT_TOKEN=old" not in text


def test_save_telegram_config_has_no_secret(tmp_path, monkeypatch):
    _point_config_to(tmp_path, monkeypatch)
    config.save_bot_token("123456:SECRET")
    config.save_telegram_config(enabled=True, owner_ids=[42])

    settings_text = config.SETTINGS_PATH.read_text(encoding="utf-8")
    assert "SECRET" not in settings_text
    assert "token" not in settings_text.lower()
    data = json.loads(settings_text)
    assert data == {"config_version": config.CONFIG_VERSION, "telegram": {"enabled": True, "owner_ids": [42]}}


# -- telegram_settings read path ------------------------------------------------------


def test_telegram_settings_reads_migrated_file_and_env_token(tmp_path, monkeypatch):
    _point_config_to(tmp_path, monkeypatch)
    config.save_telegram_config(enabled=True, owner_ids=[10, 20])
    monkeypatch.setattr(config, "load_env", lambda: None)
    monkeypatch.setenv("BOT_TOKEN", "env-token")

    settings = config.telegram_settings()

    assert settings.enabled is True
    assert settings.owner_ids == frozenset({10, 20})
    assert settings.bot_token == "env-token"


# -- wizard flow ----------------------------------------------------------------------


def test_wizard_run_persists_configuration(tmp_path, monkeypatch):
    from mute.cli.screens import wizard

    _point_config_to(tmp_path, monkeypatch)
    answers = iter(["123456:WIZ", "111, 222"])
    monkeypatch.setattr(wizard.Prompt, "ask", staticmethod(lambda *a, **k: next(answers)))
    monkeypatch.setattr(wizard.Confirm, "ask", staticmethod(lambda *a, **k: True))
    monkeypatch.setattr(wizard.theme, "pause", lambda *a, **k: None)

    wizard.run()

    assert config.ENV_PATH.read_text(encoding="utf-8").strip() == "BOT_TOKEN=123456:WIZ"
    data = json.loads(config.SETTINGS_PATH.read_text(encoding="utf-8"))
    assert data == {"config_version": config.CONFIG_VERSION, "telegram": {"enabled": True, "owner_ids": [111, 222]}}


def test_wizard_parse_owner_ids_accepts_various_separators():
    from mute.cli.screens import wizard

    assert wizard._parse_owner_ids("111, 222 333") == [111, 222, 333]
    assert wizard._parse_owner_ids("42") == [42]
    assert wizard._parse_owner_ids("abc") == []
