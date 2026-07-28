"""Application logging — per workspace.

Logging is fully independent from the CLI: nothing is written to the console, so the Rich
interface stays clean. Every **workspace owns its own logs**; each channel writes to its own
rotating file inside the active workspace's ``logs/`` folder::

    workspaces/<name>/logs/app.log             — general application activity
    workspaces/<name>/logs/api.log             — integration API client
    workspaces/<name>/logs/backup.log          — backup module
    workspaces/<name>/logs/migration.log       — migration module
    workspaces/<name>/logs/group_checker.log   — group checker module

Call :func:`use_workspace` when a workspace becomes active to (re)point all channels at its
logs folder. Until then, logging is a no-op (there is no global log). Use :func:`get_logger`
with a channel name.
"""

from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

_ROOT_NAME = "mute"
_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
_MAX_BYTES = 1_000_000
_BACKUP_COUNT = 3

CHANNEL_FILES: dict[str, str] = {
    "app": "app.log",
    "api": "api.log",
    "backup": "backup.log",
    "migration": "migration.log",
    "group_checker": "group_checker.log",
    "group_manager": "group_manager.log",
}

_current_dir: Path | None = None
_loggers: dict[str, logging.Logger] = {}


def _filename(channel: str) -> str:
    return CHANNEL_FILES.get(channel, "app.log")


def _make_handler(directory: Path, filename: str) -> RotatingFileHandler:
    directory.mkdir(parents=True, exist_ok=True)
    handler = RotatingFileHandler(
        directory / filename,
        maxBytes=_MAX_BYTES,
        backupCount=_BACKUP_COUNT,
        encoding="utf-8",
    )
    handler.setLevel(logging.INFO)
    handler.setFormatter(logging.Formatter(_FORMAT))
    return handler


def _refresh(channel: str, logger: logging.Logger) -> None:
    for handler in list(logger.handlers):
        logger.removeHandler(handler)
        handler.close()
    if _current_dir is not None:
        logger.addHandler(_make_handler(_current_dir, _filename(channel)))
    else:
        logger.addHandler(logging.NullHandler())


def get_logger(channel: str = "app") -> logging.Logger:
    """Return the logger for a channel, targeting the active workspace's logs folder."""
    if channel in _loggers:
        return _loggers[channel]
    logger = logging.getLogger(f"{_ROOT_NAME}.{channel}")
    logger.setLevel(logging.INFO)
    logger.propagate = False
    _loggers[channel] = logger
    _refresh(channel, logger)
    return logger


def use_workspace(logs_dir: Path) -> None:
    """Point every logging channel at the given workspace ``logs/`` folder."""
    global _current_dir
    _current_dir = Path(logs_dir)
    for channel, logger in _loggers.items():
        _refresh(channel, logger)
