"""What the entry points (CLI, HTTP) can ask of the application, assembled by bootstrap."""

from collections.abc import Callable, Iterable
from dataclasses import dataclass
from pathlib import Path

from lookout.application.digest_jobs import DigestJobs
from lookout.application.digester import Digester, DigestRepository
from lookout.application.iconify import Iconify
from lookout.application.personalize import Personalize
from lookout.application.ports import Clock, ItemRepository
from lookout.application.reassess import Reassess
from lookout.application.refile import Refile
from lookout.application.registry import Registry
from lookout.application.runs import RunCoordinator, RunReport
from lookout.application.source_types import SourceTypeInfo
from lookout.application.sources import SourceDirectory
from lookout.application.triage import Inbox, Triage


@dataclass(frozen=True, slots=True)
class Check:
    """One line of the doctor report."""

    name: str
    ok: bool
    detail: str


@dataclass(frozen=True, slots=True)
class Services:
    """The use cases, plus the few operations that need wiring knowledge."""

    items: ItemRepository
    triage: Triage
    inbox: Inbox
    reassess: Reassess
    personalize: Personalize
    sources: SourceDirectory
    registry: Registry
    source_types: tuple[SourceTypeInfo, ...]
    runs: RunCoordinator
    clock: Clock
    run: Callable[[], RunReport]
    doctor: Callable[[], tuple[Check, ...]]
    seed_demo: Callable[[], int]
    export: Callable[[], Iterable[str]]
    refile: Refile
    iconify: Iconify
    digester: Digester
    digests: DigestRepository
    digest_jobs: DigestJobs
    schedule_minutes: int
    dashboard_dir: Path
    close: Callable[[], None]
