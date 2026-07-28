"""Execution Report — audit trail for every Group Manager Execute."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping

from ....core.jsonio import write_json_atomic
from ....core.workspace import Workspace

REPORT_VERSION = 1
MANAGER_NAME = "group"
MAX_REPORTS = 3


@dataclass(frozen=True)
class ResultEntry:
    username: str
    status: str  # success | failed | skipped
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {"username": self.username, "status": self.status}
        if self.error:
            payload["error"] = self.error
        return payload


@dataclass(frozen=True)
class ReportSummary:
    matched: int
    success: int
    failed: int
    skipped: int = 0

    def to_dict(self) -> dict[str, int]:
        return asdict(self)


@dataclass
class ExecutionReport:
    version: int
    manager: str
    action: str
    started_at: str
    finished_at: str
    duration_ms: int
    query: Mapping[str, Any]
    summary: ReportSummary
    results: list[ResultEntry] = field(default_factory=list)
    path: Path | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": self.version,
            "manager": self.manager,
            "action": self.action,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "duration_ms": self.duration_ms,
            "query": dict(self.query),
            "summary": self.summary.to_dict(),
            "results": [entry.to_dict() for entry in self.results],
        }


def build_report(
    *,
    action: str,
    started_at: datetime,
    finished_at: datetime,
    query: Mapping[str, Any],
    results: list[ResultEntry],
) -> ExecutionReport:
    success = sum(1 for entry in results if entry.status == "success")
    failed = sum(1 for entry in results if entry.status == "failed")
    skipped = sum(1 for entry in results if entry.status == "skipped")
    duration_ms = max(0, int((finished_at - started_at).total_seconds() * 1000))
    return ExecutionReport(
        version=REPORT_VERSION,
        manager=MANAGER_NAME,
        action=action,
        started_at=started_at.isoformat(timespec="seconds"),
        finished_at=finished_at.isoformat(timespec="seconds"),
        duration_ms=duration_ms,
        query=dict(query),
        summary=ReportSummary(
            matched=len(results),
            success=success,
            failed=failed,
            skipped=skipped,
        ),
        results=list(results),
    )


def save_report(workspace: Workspace, report: ExecutionReport) -> Path:
    """Persist the report under ``reports/`` and keep only the latest ``MAX_REPORTS``."""
    workspace.ensure_dirs()
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    slug = _action_slug(report.action)
    path = workspace.reports_dir / f"{stamp}-{report.manager}-{slug}.json"
    if path.exists():
        for index in range(2, 1000):
            candidate = workspace.reports_dir / f"{stamp}-{report.manager}-{slug}-{index}.json"
            if not candidate.exists():
                path = candidate
                break
    write_json_atomic(path, report.to_dict())
    report.path = path
    _enforce_retention(workspace.reports_dir)
    return path


def list_reports(workspace: Workspace) -> list[Path]:
    if not workspace.reports_dir.is_dir():
        return []
    return sorted(
        (
            path
            for path in workspace.reports_dir.glob("*-group-*.json")
            if path.is_file()
        ),
        key=lambda path: path.name,
    )


def _enforce_retention(reports_dir: Path) -> None:
    files = sorted(
        (path for path in reports_dir.glob("*-group-*.json") if path.is_file()),
        key=lambda path: path.name,
    )
    excess = len(files) - MAX_REPORTS
    for path in files[: max(0, excess)]:
        try:
            path.unlink()
        except OSError:
            continue


def _action_slug(action: str) -> str:
    return action.replace("_", "-").strip("-") or "action"


def format_duration_seconds(duration_ms: int) -> str:
    seconds = max(0, round(duration_ms / 1000))
    return f"{seconds}s"
