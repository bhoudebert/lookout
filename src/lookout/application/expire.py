"""Untouched items leave the inbox, old entries stay out (openspec: retention, ADR 0016)."""

from datetime import timedelta

from lookout.application.ports import Clock, ItemRepository
from lookout.application.ports_sources import SourceFetcher
from lookout.domain.priority import Priority
from lookout.domain.raw import RawItem
from lookout.domain.retention import Retention


class Expire:
    """Moves untouched new or seen items to ``expired``, by how urgent they were. No signal is recorded."""

    def __init__(self, items: ItemRepository, clock: Clock, retention: Retention) -> None:
        self._items = items
        self._clock = clock
        self._retention = retention

    def run(self) -> int:
        """Expire what is due; returns how many items moved."""
        now = self._clock.now()
        moved = 0
        for priority in Priority:
            limit = self._retention.expiry(priority)
            if limit is None:
                continue
            for item in self._items.untouched_before(priority, now - limit):
                self._items.save(item.expire())
                moved += 1
        return moved


class AgeLimited:
    """A source without the entries published more than ``max_age_days`` ago; undated ones stay."""

    def __init__(self, inner: SourceFetcher, max_age_days: int, clock: Clock) -> None:
        self._inner = inner
        self._max_age = timedelta(days=max_age_days)
        self._clock = clock

    @property
    def name(self) -> str:
        return self._inner.name

    def fetch(self) -> tuple[RawItem, ...]:
        """The inner source's entries that are recent enough."""
        raws = self._inner.fetch()
        if self._max_age == timedelta(0):
            return raws
        oldest = self._clock.now() - self._max_age
        return tuple(r for r in raws if r.published_at is None or r.published_at >= oldest)
