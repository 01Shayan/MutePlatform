"""Durable JSON persistence helpers.

Every JSON file in the platform is written through :func:`write_json_atomic`, which writes to a
temporary file in the same directory, flushes and ``fsync``s it, then atomically replaces the
target with ``os.replace``. If anything fails mid-write, the previous file is left untouched and
the temporary file is discarded — a crash or full disk can never leave a half-written config,
registry, manifest, backup, or history file.

:func:`unique_path` derives a collision-free path for timestamped files (backups, history) so a
new record never overwrites an existing one while still sorting chronologically.
"""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any


def write_json_atomic(
    path: Path | str,
    data: Any,
    *,
    indent: int = 2,
    ensure_ascii: bool = True,
    mode: int | None = None,
) -> Path:
    """Serialize ``data`` to ``path`` atomically (temp file → flush → fsync → ``os.replace``).

    On any failure the original ``path`` is preserved and the temporary file is removed. When
    ``mode`` is given it is applied to the temporary file before the replace, so the final file
    never briefly exists with default permissions.
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(data, indent=indent, ensure_ascii=ensure_ascii)

    fd, tmp_name = tempfile.mkstemp(
        dir=str(path.parent), prefix=f".{path.name}.", suffix=".tmp"
    )
    tmp_path = Path(tmp_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        if mode is not None:
            try:
                os.chmod(tmp_path, mode)
            except OSError:  # best-effort on platforms without chmod semantics
                pass
        os.replace(tmp_path, path)
    except BaseException:
        try:
            tmp_path.unlink()
        except OSError:
            pass
        raise
    return path


def unique_path(directory: Path | str, stem: str, suffix: str) -> Path:
    """Return ``directory/stem+suffix``, appending ``_2``, ``_3`` … if the name already exists.

    Chronological ordering is preserved: the timestamped ``stem`` is the primary sort key, and
    ``_`` sorts after ``.`` so the un-suffixed (earliest) file of a same-timestamp group always
    sorts ahead of its later siblings.
    """
    directory = Path(directory)
    candidate = directory / f"{stem}{suffix}"
    if not candidate.exists():
        return candidate
    counter = 2
    while True:
        candidate = directory / f"{stem}_{counter}{suffix}"
        if not candidate.exists():
            return candidate
        counter += 1
