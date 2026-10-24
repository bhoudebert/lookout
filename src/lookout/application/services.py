"""What the entry points (CLI, HTTP) can ask of the application, assembled by bootstrap."""

from collections.abc import Callable
from dataclasses import dataclass

from lookout.application.enrich import EnrichReport
from lookout.application.ingest import IngestReport
from lookout.application.ports import Clock, ItemRepository
from lookout.application.reassess import Reassess
from lookout.application.triage import Inbox, Triage


@dataclass(frozen=True, slots=True)
class Check:
    """One line of the doctor report."""

    name: str
    ok: bool
    detail: str


@dataclass(frozen=True, slots=True)
class RunReport:
    """What one run did: sources fetched, then items read."""

    ingest: IngestReport
    enrich: EnrichReport


@dataclass(frozen=True, slots=True)
class Services:
    """The use cases, plus the few operations that need wiring knowledge."""

    items: ItemRepository
    triage: Triage
    inbox: Inbox
    reassess: Reassess
    clock: Clock
    run: Callable[[], RunReport]
    doctor: Callable[[], tuple[Check, ...]]
    seed_demo: Callable[[], int]
    close: Callable[[], None]
