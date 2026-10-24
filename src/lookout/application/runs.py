"""One run at a time, started from anywhere (openspec: scheduling, "No overlap")."""

import threading
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime

from lookout.application.enrich import EnrichReport
from lookout.application.ingest import IngestReport
from lookout.application.ports import Clock


@dataclass(frozen=True, slots=True)
class RunReport:
    """What one run did: sources fetched, then items read."""

    ingest: IngestReport
    enrich: EnrichReport


@dataclass(frozen=True, slots=True)
class RunStatus:
    """Where the current or last run stands."""

    running: bool = False
    started_at: datetime | None = None
    finished_at: datetime | None = None
    report: RunReport | None = None
    error: str | None = None


def spawn_thread(work: Callable[[], None]) -> None:
    """Run ``work`` on a background thread."""
    threading.Thread(target=work, daemon=True, name="lookout-run").start()


class RunCoordinator:
    """Starts runs in the background and refuses to overlap them."""

    def __init__(
        self,
        run: Callable[[], RunReport],
        clock: Clock,
        spawn: Callable[[Callable[[], None]], None] = spawn_thread,
    ) -> None:
        self._run = run
        self._clock = clock
        self._spawn = spawn
        self._lock = threading.Lock()
        self._status = RunStatus()

    def status(self) -> RunStatus:
        """The current or last run."""
        with self._lock:
            return self._status

    def start(self) -> tuple[RunStatus, bool]:
        """Start a run unless one is in progress; returns the status and whether this call started it."""
        with self._lock:
            if self._status.running:
                return self._status, False
            self._status = RunStatus(running=True, started_at=self._clock.now())
            started = self._status
        self._spawn(self._work)
        return started, True

    def _work(self) -> None:
        report: RunReport | None = None
        error: str | None = None
        try:
            report = self._run()
        except Exception as problem:
            error = f"{type(problem).__name__}: {problem}"
        with self._lock:
            self._status = RunStatus(
                running=False,
                started_at=self._status.started_at,
                finished_at=self._clock.now(),
                report=report,
                error=error,
            )
