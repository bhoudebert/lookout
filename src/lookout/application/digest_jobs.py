"""Digests written in the background, followed from anywhere (openspec: digest)."""

import hashlib
import threading
from collections.abc import Callable
from dataclasses import dataclass, replace
from datetime import datetime
from enum import StrEnum

from lookout.application.digester import DigestCancelledError, Digester, DigestError, EmptyDigestError
from lookout.application.ports import Clock, InboxQuery
from lookout.application.runs import spawn_thread

KEPT_FINISHED = 10


class JobState(StrEnum):
    """Where a digest being written stands."""

    RUNNING = "running"
    DONE = "done"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass(frozen=True, slots=True)
class DigestJob:
    """A digest being written, or how the last attempts ended. Kept in memory only."""

    id: str
    scope: str
    started_at: datetime
    state: JobState = JobState.RUNNING
    section: str = ""
    section_number: int = 0
    sections_total: int = 0
    tokens: int = 0
    finished_at: datetime | None = None
    error: str | None = None
    digest_id: str | None = None


class UnknownJobError(Exception):
    """No job has this id."""


class JobRunningError(Exception):
    """A job that is still running cannot be dismissed."""


class DigestJobs:
    """Writes one digest at a time on a background thread, and remembers how it went until dismissed."""

    def __init__(
        self,
        digester: Digester,
        clock: Clock,
        spawn: Callable[[Callable[[], None]], None] = spawn_thread,
    ) -> None:
        self._digester = digester
        self._clock = clock
        self._spawn = spawn
        self._lock = threading.Lock()
        self._jobs: dict[str, DigestJob] = {}
        self._stopping: set[str] = set()

    def jobs(self) -> tuple[DigestJob, ...]:
        """The running job first, then the finished ones, newest first."""
        with self._lock:
            return tuple(
                sorted(
                    self._jobs.values(),
                    key=lambda j: (j.state is not JobState.RUNNING, -j.started_at.timestamp()),
                )
            )

    def start(self, query: InboxQuery, scope: str) -> tuple[DigestJob, bool]:
        """Start writing unless one is being written; returns the job and whether this call started it."""
        with self._lock:
            running = next((j for j in self._jobs.values() if j.state is JobState.RUNNING), None)
            if running is not None:
                return running, False
            now = self._clock.now()
            job = DigestJob(
                hashlib.sha256(f"{now.isoformat()}|{scope}".encode()).hexdigest()[:12], scope, now
            )
            self._jobs[job.id] = job
            self._forget_old()
        self._spawn(lambda: self._work(job.id, query))
        return job, True

    def cancel(self, job_id: str) -> DigestJob:
        """Ask a running job to stop; it stops at the next piece of text the model writes."""
        with self._lock:
            job = self._get(job_id)
            if job.state is JobState.RUNNING:
                self._stopping.add(job_id)
            return job

    def dismiss(self, job_id: str) -> None:
        """Forget a finished job."""
        with self._lock:
            if self._get(job_id).state is JobState.RUNNING:
                msg = "the digest is still being written: cancel it first"
                raise JobRunningError(msg)
            del self._jobs[job_id]

    def _get(self, job_id: str) -> DigestJob:
        if job_id not in self._jobs:
            raise UnknownJobError(job_id)
        return self._jobs[job_id]

    def _forget_old(self) -> None:
        finished = [j for j in self._jobs.values() if j.state is not JobState.RUNNING]
        finished.sort(key=lambda j: j.started_at, reverse=True)
        for job in finished[KEPT_FINISHED:]:
            del self._jobs[job.id]

    def _update(self, job_id: str, **changes: object) -> None:
        with self._lock:
            self._jobs[job_id] = replace(self._jobs[job_id], **changes)  # type: ignore[arg-type]

    def _work(self, job_id: str, query: InboxQuery) -> None:
        def update(**changes: object) -> None:
            self._update(job_id, **changes)

        def stopping() -> bool:
            with self._lock:
                return job_id in self._stopping

        try:
            digest = self._digester.create(query, self._jobs[job_id].scope, _Watch(update, stopping))
        except DigestCancelledError:
            self._finish(job_id, JobState.CANCELLED)
        except (DigestError, EmptyDigestError) as error:
            self._finish(job_id, JobState.FAILED, error=str(error))
        except Exception as problem:
            self._finish(job_id, JobState.FAILED, error=f"{type(problem).__name__}: {problem}")
        else:
            self._finish(job_id, JobState.DONE, digest_id=digest.id)

    def _finish(
        self, job_id: str, state: JobState, *, error: str | None = None, digest_id: str | None = None
    ) -> None:
        with self._lock:
            self._stopping.discard(job_id)
        self._update(job_id, state=state, finished_at=self._clock.now(), error=error, digest_id=digest_id)


class _Watch:
    """What one job tells the world while its digest is written, and how the world stops it."""

    def __init__(self, update: Callable[..., None], stopping: Callable[[], bool]) -> None:
        self._update = update
        self._stopping = stopping
        self._tokens = 0
        self._number = 0

    def planned(self, sections: int) -> None:
        self._update(sections_total=sections)

    def started(self, title: str) -> None:
        self._number += 1
        self._update(section=title, section_number=self._number)

    def wrote(self, tokens: int) -> None:
        self._tokens += tokens
        self._update(tokens=self._tokens)

    def stopped(self) -> bool:
        return self._stopping()
