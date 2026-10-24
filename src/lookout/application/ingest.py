"""Fetch sources, store new items once, keep failures from spreading (openspec: source-ingestion)."""

from dataclasses import dataclass, field, replace
from datetime import timedelta

from lookout.application.ports import Clock, ItemRepository
from lookout.application.ports_sources import SourceError, SourceFetcher, SourceStatus, SourceStatusRepository
from lookout.domain.item import Item, item_id
from lookout.domain.policy import PriorityPolicy
from lookout.domain.raw import RawItem
from lookout.domain.stack import Stack
from lookout.domain.text import clean_text

BACKOFF_BASE = timedelta(minutes=5)
BACKOFF_MAX = timedelta(hours=6)


@dataclass(frozen=True, slots=True)
class SourceReport:
    """What one source did in a run."""

    name: str
    fetched: int = 0
    new: int = 0
    error: str | None = None
    skipped: bool = False


@dataclass(frozen=True, slots=True)
class IngestReport:
    """What a whole ingest did."""

    sources: tuple[SourceReport, ...] = field(default_factory=tuple)

    @property
    def new(self) -> int:
        return sum(s.new for s in self.sources)


class Ingest:
    """Turns raw entries into stored items, once each."""

    def __init__(
        self,
        items: ItemRepository,
        statuses: SourceStatusRepository,
        clock: Clock,
        policy: PriorityPolicy,
        stack: Stack,
        *,
        body_limit: int = 4000,
    ) -> None:
        self._items = items
        self._statuses = statuses
        self._clock = clock
        self._policy = policy
        self._stack = stack
        self._body_limit = body_limit

    def run(self, fetchers: tuple[SourceFetcher, ...]) -> IngestReport:
        """Run every fetcher that is not backing off; one failing source never stops the others."""
        return IngestReport(tuple(self._run_one(f) for f in fetchers))

    def _run_one(self, fetcher: SourceFetcher) -> SourceReport:
        now = self._clock.now()
        status = self._statuses.get(fetcher.name)
        if status.next_attempt is not None and status.next_attempt > now:
            return SourceReport(fetcher.name, skipped=True, error=status.last_error)
        try:
            raws = fetcher.fetch()
        except SourceError as error:
            failures = status.failures + 1
            wait = min(BACKOFF_BASE * 2 ** (failures - 1), BACKOFF_MAX)
            self._statuses.save(
                replace(
                    status, last_run=now, last_error=str(error), failures=failures, next_attempt=now + wait
                )
            )
            return SourceReport(fetcher.name, error=str(error))
        new = sum(self._store(raw) for raw in raws)
        self._statuses.save(SourceStatus(fetcher.name, last_run=now, items_seen=status.items_seen + new))
        return SourceReport(fetcher.name, fetched=len(raws), new=new)

    def _store(self, raw: RawItem) -> int:
        """Store one entry; returns 1 when it is a new item, 0 when it only added a source name."""
        ident = item_id(raw.url)
        existing = self._items.get(ident)
        if existing is not None:
            if raw.source not in existing.sources:
                self._items.save(replace(existing, sources=(*existing.sources, raw.source)))
            return 0
        title = clean_text(raw.title, 300)
        body = clean_text(raw.body, self._body_limit)
        matches = self._stack.match(f"{title}\n{body}", raw.advisory)
        decision = self._policy.decide(advisory=raw.advisory, stack_matches=matches, enrichment=None)
        item = Item(
            id=ident,
            url=raw.url,
            title=title,
            body=body,
            published_at=raw.published_at or self._clock.now(),
            sources=(raw.source,),
            advisory=raw.advisory,
        ).assessed(decision.priority, decision.reason, matches)
        self._items.save(item)
        return 1
