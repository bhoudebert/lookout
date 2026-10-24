"""Have the model read new items, within a daily budget (openspec: enrichment)."""

from dataclasses import dataclass

from lookout.application.ports import Clock, ItemRepository
from lookout.application.ports_sources import Enricher, EnrichmentError, UsageRepository
from lookout.domain.policy import PriorityPolicy


@dataclass(frozen=True, slots=True)
class EnrichReport:
    """What an enrichment pass did."""

    enriched: int = 0
    failed: int = 0
    waiting: int = 0


class Enrich:
    """Reads items that have no enrichment yet; priority is recomputed from the new reading."""

    def __init__(
        self,
        items: ItemRepository,
        enricher: Enricher,
        usage: UsageRepository,
        clock: Clock,
        policy: PriorityPolicy,
        *,
        daily_limit: int,
    ) -> None:
        self._items = items
        self._enricher = enricher
        self._usage = usage
        self._clock = clock
        self._policy = policy
        self._daily_limit = daily_limit

    def run(self) -> EnrichReport:
        """Most urgent items first, so a spent budget never starves an emergency."""
        day = self._clock.now().date().isoformat()
        pending = self._items.pending_enrichment()
        enriched = failed = 0
        for position, item in enumerate(pending):
            if self._usage.calls_on(day) >= self._daily_limit:
                return EnrichReport(enriched, failed, waiting=len(pending) - position)
            self._usage.record_call(day)
            try:
                reading = self._enricher.enrich(item)
            except EnrichmentError:
                self._items.save(item.enrichment_gave_up())
                failed += 1
                continue
            decision = self._policy.decide(
                advisory=item.advisory, stack_matches=item.stack_matches, enrichment=reading
            )
            self._items.save(
                item.enriched(reading).assessed(decision.priority, decision.reason, item.stack_matches)
            )
            enriched += 1
        return EnrichReport(enriched, failed)
