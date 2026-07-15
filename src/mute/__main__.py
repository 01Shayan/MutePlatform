"""Entry point for Mute.

Run with:

    PYTHONPATH=src python -m mute
"""

from __future__ import annotations

from .cli.app import run

if __name__ == "__main__":
    raise SystemExit(run())
