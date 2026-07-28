"""Shared project metadata — the single source of truth.

Never hardcode these values throughout the project. Import them from here (directly, or via
``theme`` for the UI layer) so a change in one place propagates everywhere.
"""

from __future__ import annotations

from datetime import datetime

from .. import __version__

APP_NAME = "Mute Platform"
BRAND = "Mute"
TAGLINE = "Intelligent VPN Operations Platform"
VERSION = __version__
DEVELOPER = "01Shayan"
GITHUB_URL = "https://github.com/01Shayan/MutePlatform"
COPYRIGHT = f"© {datetime.now():%Y} {DEVELOPER}"
FOOTER_TEXT = "Powered by 🧠 Mute"

# Identity written into backup metadata — the short brand, kept stable across renames.
TOOL_NAME = BRAND