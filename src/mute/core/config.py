"""Application configuration: settings, secrets, first-run detection, and migration.

Two stores, with a strict separation:

* ``config/settings.json`` — non-secret settings only: ``config_version`` and the Telegram
  ``enabled`` / ``owner_ids`` values.
* ``.env`` — secrets only. The Telegram ``BOT_TOKEN`` lives here and is never written to JSON.

The schema is versioned by a top-level ``config_version``. Older layouts are upgraded
automatically on startup, so after a future update the user only needs ``git pull`` — never a
manual edit of a configuration file.

The ``.env`` file also supplies *default values* used to seed the first workspace and to
pre-fill the "add workspace" form; it never overrides a saved workspace.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass

from dotenv import load_dotenv

from .paths import CONFIG_DIR, ENV_PATH, SETTINGS_PATH
from .profiles import Profile

# Bump when the settings.json schema changes; ``migrate_settings`` upgrades older files.
CONFIG_VERSION = 2

# The complete, canonical settings.json — settings.json stores ONLY these keys.
_DEFAULT_TELEGRAM = {"enabled": False, "owner_ids": []}


def _default_settings() -> dict:
    return {"config_version": CONFIG_VERSION, "telegram": dict(_DEFAULT_TELEGRAM)}


# -- first-run detection --------------------------------------------------------------

def is_first_run() -> bool:
    """True when the installation is not fully configured; the Setup Wizard must run.

    The existence of ``config/settings.json`` alone is NOT sufficient — a fresh clone (or a
    partial setup) may have a settings file yet still lack the secrets and owner IDs the
    Telegram interface needs. The installation is considered complete ONLY when every condition
    below holds:

    * ``config/settings.json`` exists
    * ``.env`` exists
    * ``BOT_TOKEN`` is present and non-empty in ``.env``
    * ``telegram.owner_ids`` contains at least one valid ID

    If any condition is unmet, the wizard should launch. This function has no side effects: it
    never creates or migrates configuration files.
    """
    if not SETTINGS_PATH.exists():
        return True
    if not ENV_PATH.exists():
        return True
    if not _read_env_var("BOT_TOKEN"):
        return True
    if not _settings_owner_ids():
        return True
    return False


def _settings_owner_ids() -> list[int]:
    """Return the valid owner IDs recorded in ``settings.json`` (empty if none/unreadable)."""
    telegram = _read_settings().get("telegram")
    telegram = telegram if isinstance(telegram, dict) else {}
    raw = telegram.get("owner_ids", [])
    return _coerce_owner_ids(raw if isinstance(raw, list) else [])


# -- reading / writing settings.json --------------------------------------------------

def _read_settings() -> dict:
    try:
        data = json.loads(SETTINGS_PATH.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (json.JSONDecodeError, OSError):
        return {}


def _write_settings(settings: dict) -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    SETTINGS_PATH.write_text(json.dumps(settings, indent=2), encoding="utf-8")


def migrate_settings(settings: dict) -> tuple[dict, bool]:
    """Return ``(clean_settings, changed)`` upgraded to the current schema.

    Preserves the Telegram ``enabled`` / ``owner_ids`` values while dropping legacy keys
    (e.g. inert v0.1 placeholders and the old nested ``telegram.config_version``) and moving
    ``config_version`` to the top level.
    """
    telegram = settings.get("telegram")
    telegram = telegram if isinstance(telegram, dict) else {}

    owner_ids_raw = telegram.get("owner_ids", [])
    owner_ids = _coerce_owner_ids(owner_ids_raw if isinstance(owner_ids_raw, list) else [])

    clean = {
        "config_version": CONFIG_VERSION,
        "telegram": {"enabled": bool(telegram.get("enabled", False)), "owner_ids": owner_ids},
    }
    changed = clean != settings
    return clean, changed


def ensure_settings() -> None:
    """Create ``config/settings.json`` if absent, otherwise migrate it in place."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    if not SETTINGS_PATH.exists():
        _write_settings(_default_settings())
        return
    clean, changed = migrate_settings(_read_settings())
    if changed:
        _write_settings(clean)


def _coerce_owner_ids(values) -> list[int]:
    result: list[int] = []
    for value in values:
        try:
            result.append(int(value))
        except (TypeError, ValueError):
            continue
    return result


# -- wizard write helpers -------------------------------------------------------------

def save_bot_token(token: str) -> None:
    """Persist the Telegram bot token to ``.env`` only, preserving other variables."""
    set_env_var("BOT_TOKEN", token.strip())


def save_telegram_config(*, enabled: bool, owner_ids) -> None:
    """Persist non-secret Telegram settings to ``config/settings.json``."""
    ensure_settings()
    settings = _read_settings()
    settings["config_version"] = CONFIG_VERSION
    settings["telegram"] = {"enabled": bool(enabled), "owner_ids": _coerce_owner_ids(owner_ids)}
    _write_settings(settings)


def _read_env_var(name: str) -> str:
    """Read a single variable's value straight from ``.env``.

    Reads the file directly (not ``os.environ``) so first-run detection is deterministic and
    free of side effects, and works even before ``load_env`` has run. Returns ``""`` when the
    file or the key is missing. Surrounding quotes, if present, are stripped.
    """
    if not ENV_PATH.exists():
        return ""
    for line in ENV_PATH.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, _, value = stripped.partition("=")
        if key.strip() == name:
            value = value.strip()
            if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
                value = value[1:-1]
            return value
    return ""


def set_env_var(name: str, value: str) -> None:
    """Insert or update ``name=value`` in ``.env`` without disturbing other entries."""
    lines: list[str] = []
    if ENV_PATH.exists():
        lines = ENV_PATH.read_text(encoding="utf-8").splitlines()
    prefix = f"{name}="
    replaced = False
    for index, line in enumerate(lines):
        stripped = line.lstrip()
        if stripped.startswith(prefix) or stripped.startswith(f"{name} ="):
            lines[index] = f"{name}={value}"
            replaced = True
            break
    if not replaced:
        lines.append(f"{name}={value}")
    ENV_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


# -- Telegram settings (read) ---------------------------------------------------------

_TRUE_VALUES = {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class TelegramSettings:
    enabled: bool
    owner_ids: frozenset[int]
    bot_token: str


def _env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None or value.strip() == "":
        return default
    return value.strip().lower() in _TRUE_VALUES


def load_env() -> None:
    """Load variables from a local ``.env`` file if present."""
    load_dotenv()


def telegram_settings() -> TelegramSettings:
    """Load Telegram settings while keeping the bot token outside JSON configuration."""
    ensure_settings()
    load_env()
    try:
        settings = json.loads(SETTINGS_PATH.read_text(encoding="utf-8"))
        telegram = settings["telegram"]
        owner_ids = frozenset(int(value) for value in telegram["owner_ids"])
    except (json.JSONDecodeError, OSError, KeyError, TypeError, ValueError) as exc:
        raise ValueError("Telegram settings are invalid.") from exc
    return TelegramSettings(
        enabled=bool(telegram.get("enabled")),
        owner_ids=owner_ids,
        bot_token=os.getenv("BOT_TOKEN", "").strip(),
    )


def env_defaults() -> Profile | None:
    """Build a default profile from environment variables, or ``None`` if unconfigured."""
    load_env()

    base_url = os.getenv("PASARGUARD_BASE_URL", "").strip()
    if not base_url:
        return None

    return Profile(
        name=os.getenv("PASARGUARD_PROFILE", "default").strip() or "default",
        base_url=base_url,
        username=(os.getenv("PASARGUARD_USERNAME") or "").strip() or None,
        password=(os.getenv("PASARGUARD_PASSWORD") or "").strip() or None,
        token=(os.getenv("PASARGUARD_TOKEN") or "").strip() or None,
        verify_ssl=_env_bool("PASARGUARD_VERIFY_SSL", True),
    )
