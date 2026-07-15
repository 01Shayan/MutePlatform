"""Lightweight job execution history.

Every completed operation writes one small JSON file under its workspace's ``history/`` folder.
This is NOT analytics — just a durable record of what ran, when, and how it went. Future modules
(and eventually Mute's decision support) can build on it.

Example ``workspaces/Production/history/2026-07-10_18-22_backup.json``::

    {"type": "backup", "status": "success", "workspace": "Production",
     "integration": "PasarGuard", "users": 2130, "duration": 8.3}
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from .jsonio import unique_path, write_json_atomic
from .logging import get_logger

logger = get_logger("app")


def record_job(data: dict, *, jobs_dir: Path) -> Path:
    """Write a single job-history record into ``jobs_dir`` and return its path.

    The filename carries a second-precision timestamp and, if that name is already taken, a
    numeric suffix — so two jobs of the same type in the same minute (or second) never overwrite
    each other, while the timestamp prefix keeps the files chronologically ordered.
    """
    jobs_dir.mkdir(parents=True, exist_ok=True)
    job_type = str(data.get("type", "job"))
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    path = unique_path(jobs_dir, f"{timestamp}_{job_type}", ".json")

    payload = {"created_at": datetime.now().isoformat(timespec="seconds"), **data}
    write_json_atomic(path, payload, ensure_ascii=False)
    logger.info("Recorded job history → %s", path)
    return path
