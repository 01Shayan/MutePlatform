"""Mute — an intelligent business platform for VPN operators."""

from __future__ import annotations

from pathlib import Path


def _read_version() -> str:
    """Prefer the repository VERSION file; fall back for editable installs without it."""
    version_file = Path(__file__).resolve().parents[2] / "VERSION"
    try:
        text = version_file.read_text(encoding="utf-8").strip()
        if text:
            return text
    except OSError:
        pass
    return "0.3.0-dev"


__version__ = _read_version()
