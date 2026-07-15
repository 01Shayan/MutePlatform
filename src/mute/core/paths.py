"""Canonical filesystem locations.

All runtime data is anchored to the project root, so the app always reads/writes the same
places regardless of the current working directory it was launched from.

The platform is *workspace-centric*: each workspace owns all of its data under
``workspaces/<name>/`` (backups, migrations, reports, exports, logs, cache, history). The only
global config is the workspace registry (``config/workspaces.json``).
"""

from __future__ import annotations

from pathlib import Path

# .../src/mute/core/paths.py → project root is four levels up.
PROJECT_ROOT = Path(__file__).resolve().parents[3]

CONFIG_DIR = PROJECT_ROOT / "config"
WORKSPACES_DIR = PROJECT_ROOT / "workspaces"

WORKSPACES_PATH = CONFIG_DIR / "workspaces.json"
SETTINGS_PATH = CONFIG_DIR / "settings.json"

# Secrets (e.g. the Telegram BOT_TOKEN) live here — never in JSON configuration.
ENV_PATH = PROJECT_ROOT / ".env"

# Legacy locations, kept only for one-time migration into workspaces.
BACKUPS_DIR = PROJECT_ROOT / "backups"
PROFILES_PATH = CONFIG_DIR / "profiles.json"
