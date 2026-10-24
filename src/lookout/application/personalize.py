"""Learn from actions and rank inside priority bands (openspec: personalization)."""

from dataclasses import dataclass

from lookout.application.ports import Clock, ItemRepository, SignalRepository
from lookout.application.triage import ItemNotFoundError
from lookout.domain.item import Item
from lookout.domain.priority import Priority
from lookout.domain.profile import Contribution, Profile, Signal, SignalKind, learn


@dataclass(frozen=True, slots=True)
class Explanation:
    """Why an item ranks where it does: its priority and its place inside the priority."""

    priority: Priority
    priority_reason: str
    model_score: int | None
    boost: int
    contributions: tuple[Contribution, ...]


class Personalize:
    """Turns signals into a profile, and the profile into a rank adjustment on every item."""

    def __init__(
        self,
        items: ItemRepository,
        signals: SignalRepository,
        clock: Clock,
        *,
        half_life_days: float = 30.0,
        minimum_signals: int = 5,
    ) -> None:
        self._items = items
        self._signals = signals
        self._clock = clock
        self._half_life = half_life_days
        self._minimum = minimum_signals

    def profile(self) -> Profile:
        """What has been learnt so far."""
        by_id = {item.id: item for item in self._items.all()}
        return learn(
            self._signals.all(),
            by_id,
            self._clock.now(),
            half_life_days=self._half_life,
            minimum=self._minimum,
        )

    def record(self, item: Item, kind: SignalKind) -> None:
        """Remember an action and re-rank."""
        self._signals.add(Signal(item.id, kind, self._clock.now()))
        self.rerank()

    def rerank(self) -> int:
        """Apply the profile to every item; returns how many ranks changed."""
        profile = self.profile()
        changed = 0
        for item in self._items.all():
            updated = item.ranked(profile.boost(item))
            if updated != item:
                self._items.save(updated)
                changed += 1
        return changed

    def explain(self, item_id: str) -> Explanation:
        """The breakdown shown as "why this rank"."""
        item = self._items.get(item_id)
        if item is None:
            raise ItemNotFoundError(item_id)
        contributions = self.profile().contributions(item)
        score = item.enrichment.score if item.enrichment else None
        return Explanation(item.priority, item.priority_reason, score, item.boost, contributions)

    def reset(self) -> None:
        """Forget what was learnt; items stay as they are."""
        self._signals.clear()
        self.rerank()
