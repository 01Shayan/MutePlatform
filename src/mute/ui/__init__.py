"""Mute Platform Design System — shared presentation copy and icons.

CLI is the reference. Telegram mirrors the same labels and wording.
Business logic must never live here.
"""

from __future__ import annotations

from . import copy, icons, layout
from .icons import Icon
from .layout import DIVIDER, format_screen

__all__ = [
    "DIVIDER",
    "Icon",
    "copy",
    "format_screen",
    "icons",
    "layout",
]
