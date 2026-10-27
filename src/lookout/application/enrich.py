"""Have the model read new items, within a daily budget (openspec: enrichment)."""

from collections.abc import Callable, Mapping
from dataclasses import dataclass

from lookout.application.ports import Clock, ItemRepository
from lookout.application.ports_sources import Enricher, EnrichmentError, UsageRepository
from lookout.domain.channel import ChannelCatalogue
from lookout.domain.item import Item
from lookout.domain.policy import PriorityPolicy
from lookout.domain.profile import Example, Profile


@dataclass(frozen=True, slots=True)
class EnrichReport:
    """What an enrichment pass did."""

    enriched: int = 0
    failed: int = 0
    waiting: int = 0


@dataclass(frozen=True, slots=True)
class OwnModels:
    """Sources that ask for a model of their own: which model each asks for, and how to reach one."""

    asked: Callable[[], Mapping[str, str]]
    reader: Callable[[str], Enricher]


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
        profile: Callable[[], Profile] = lambda: Profile({}),
        catalogue: Callable[[], ChannelCatalogue] = ChannelCatalogue,
        examples: Callable[[], tuple[Example, ...]] = tuple,
        own_models: OwnModels | None = None,
    ) -> None:
        self._items = items
        self._enricher = enricher
        self._usage = usage
        self._clock = clock
        self._policy = policy
        self._daily_limit = daily_limit
        self._profile = profile
        self._catalogue = catalogue
        self._examples = examples
        self._own = own_models or OwnModels(dict, lambda _model: enricher)

    def run(self) -> EnrichReport:
        """Most urgent items first, so a spent budget never starves an emergency."""
        day = self._clock.now().date().isoformat()
        pending = self._items.pending_enrichment()
        profile = self._profile()
        catalogue = self._catalogue()
        examples = self._examples()
        models = self._own.asked()
        enriched = failed = 0
        for position, item in enumerate(pending):
            if self._usage.calls_on(day) >= self._daily_limit:
                return EnrichReport(enriched, failed, waiting=len(pending) - position)
            self._usage.record_call(day)
            try:
                reading = self._reader(item, models).enrich(item, catalogue.allowed(item.sources), examples)
            except EnrichmentError:
                self._items.save(item.enrichment_gave_up())
                failed += 1
                continue
            decision = self._policy.decide(
                advisory=item.advisory,
                stack_matches=item.stack_matches,
                enrichment=reading,
                age=self._clock.now() - item.published_at,
            )
            read = item.enriched(reading).assessed(decision.priority, decision.reason, item.stack_matches)
            self._items.save(read.ranked(profile.boost(read)))
            enriched += 1
        return EnrichReport(enriched, failed)

    def _reader(self, item: Item, models: Mapping[str, str]) -> Enricher:
        """The model of the first source of the item that asks for one, else the default model."""
        model = next((models[s] for s in item.sources if s in models), None)
        return self._own.reader(model) if model else self._enricher
