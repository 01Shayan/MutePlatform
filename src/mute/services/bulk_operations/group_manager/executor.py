"""Action Executor — applies planned group changes with continue-on-failure."""

from __future__ import annotations

from datetime import datetime
from typing import Callable

from ....integrations.pasarguard.client import PasarGuardClient, PasarGuardError, create_client
from ....core.workspace import Workspace
from .actions.base import PlannedChange
from .reports import ExecutionReport, ResultEntry, build_report, save_report


ProgressHook = Callable[[str, int, int], None]


def execute_planned_changes(
    workspace: Workspace,
    *,
    action: str,
    query: dict,
    planned: list[PlannedChange],
    client: PasarGuardClient | None = None,
    progress: ProgressHook | None = None,
) -> ExecutionReport:
    """Write each planned change. Failures never stop remaining users. Always returns a report."""
    api = client or create_client(workspace)
    started = datetime.now()
    results: list[ResultEntry] = []
    total = len(planned)

    for index, change in enumerate(planned, start=1):
        if progress is not None:
            progress(change.username, index, total)
        if change.before == change.after:
            results.append(ResultEntry(username=change.username, status="skipped"))
            continue
        try:
            api.modify_user(change.username, group_ids=list(change.after))
            results.append(ResultEntry(username=change.username, status="success"))
        except PasarGuardError as exc:
            results.append(
                ResultEntry(username=change.username, status="failed", error=str(exc))
            )
        except Exception as exc:  # noqa: BLE001 — continue on failure
            results.append(
                ResultEntry(username=change.username, status="failed", error=str(exc))
            )

    finished = datetime.now()
    report = build_report(
        action=action,
        started_at=started,
        finished_at=finished,
        query=query,
        results=results,
    )
    save_report(workspace, report)
    return report
