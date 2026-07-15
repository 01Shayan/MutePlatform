"""Reusable job lifecycle for long-running operations.

Every long-running module (Backup first, then others) implements a :class:`Job` and is run
through :func:`run_job`, which drives a consistent experience:

    Initialization → Confirmation → Progress → Summary → Return to Main Menu

Jobs contain no UI code: they validate/prepare, then execute using a :class:`ProgressReporter`
callback. This keeps business logic UI-agnostic and testable, while the lifecycle owns all the
Rich rendering, cancellation, and human-friendly error handling. Each stage renders only its own
compact page header (the brand banner is shown once, at startup).
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field

from rich.progress import Progress
from rich.prompt import Confirm

from ..core.logging import get_logger
from ..core.workspace import Workspace
from . import theme
from .theme import console

logger = get_logger("app")


class JobError(Exception):
    """A human-friendly failure. Its message is shown to the user as-is."""


@dataclass
class JobOutcome:
    """The result a job returns for its summary screen."""

    title: str
    rows: list[tuple[str, str]] = field(default_factory=list)
    style: str = "success"
    history: dict | None = None  # written to the workspace's history/ on success


class ProgressReporter:
    """Adapts a job's ``(message, completed, total)`` callback onto a Rich progress bar."""

    def __init__(self, progress: Progress) -> None:
        self._progress = progress
        self._task_id: int | None = None

    def __call__(self, message: str, completed: int, total: int) -> None:
        total_arg = total if total > 0 else None
        if self._task_id is None:
            self._task_id = self._progress.add_task(message, total=total_arg)
        self._progress.update(
            self._task_id, description=message, completed=completed, total=total_arg
        )


class Job(ABC):
    """Base class for a long-running operation."""

    icon: str = "•"
    title: str = "Job"
    action: str = "Run"  # workflow verb, e.g. "Export"
    description: list[str] = []  # module self-introduction, shown on its own page
    prepare_message: str = "Preparing…"
    confirm_default: bool = True

    @abstractmethod
    def prepare(self, workspace: Workspace) -> list[tuple[str, str]]:
        """Validate preconditions and return detail rows shown before confirmation.

        Raise :class:`JobError` if the job cannot proceed.
        """

    @abstractmethod
    def execute(self, workspace: Workspace, report: ProgressReporter) -> JobOutcome:
        """Perform the work, reporting progress via ``report``. Return the summary."""


def run_job(job: Job, workspace: Workspace) -> None:
    """Drive a job through the full lifecycle, always returning cleanly to the caller."""
    # 1. Initialization — the module introduces itself, then prepares -----------------
    theme.clear()
    console.print(theme.page_header(job.title, job.icon))
    console.print()
    if job.description:
        console.print(theme.body_text(job.description))
        console.print()
    try:
        with console.status(f"[muted]{job.prepare_message}[/muted]", spinner="dots"):
            details = job.prepare(workspace)
    except JobError as exc:
        _fail(job, str(exc))
        return
    except Exception as exc:  # unexpected: log full detail, show friendly message
        logger.exception("Unexpected error while preparing %s", job.title)
        _fail(job, f"An unexpected error occurred.\n{exc}")
        return

    # 2. Confirmation -----------------------------------------------------------------
    theme.page(
        f"{job.action} Confirmation",
        theme.info_panel(details),
        icon=job.icon,
    )
    if not Confirm.ask("\nProceed?", default=job.confirm_default):
        theme.notify_info("Cancelled. No changes were made.")
        theme.pause()
        return

    # 3. Progress ---------------------------------------------------------------------
    theme.clear()
    console.print(theme.page_header(f"{job.action} in Progress", job.icon))
    console.print()
    try:
        with theme.make_progress() as progress:
            outcome = job.execute(workspace, ProgressReporter(progress))
    except JobError as exc:
        _fail(job, str(exc))
        return
    except Exception as exc:
        logger.exception("Unexpected error while running %s", job.title)
        _fail(job, f"The operation failed.\n{exc}")
        return

    # 4. Summary ----------------------------------------------------------------------
    theme.page(
        f"{job.action} Summary",
        theme.summary_panel(outcome.title, outcome.rows, style=outcome.style),
        icon=job.icon,
    )
    # 5. Return -----------------------------------------------------------------------
    theme.pause()


def _fail(job: Job, detail: str) -> None:
    theme.page(
        f"{job.action} — Failed",
        theme.error_panel(f"{job.action} could not be completed", detail),
        icon=job.icon,
    )
    theme.pause()
