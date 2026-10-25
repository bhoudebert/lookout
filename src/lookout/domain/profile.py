"""What the user's actions teach (openspec: personalization). Orders items inside a priority band."""

import math
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

from lookout.domain.channel import ancestors
from lookout.domain.item import Item
from lookout.domain.rating import Rating

MAX_BOOST = 20
POINTS_PER_UNIT = 4


class SignalKind(StrEnum):
    """Things the user does that say something about taste."""

    OPEN = "open"
    STAR = "star"
    SNOOZE = "snooze"


WEIGHTS: dict[SignalKind, float] = {
    SignalKind.STAR: 3.0,
    SignalKind.OPEN: 1.0,
    SignalKind.SNOOZE: 0.0,
}
RATING_WEIGHT = 3.0
"""What a thumb is worth, up or down: as much as a star."""


@dataclass(frozen=True, slots=True)
class Signal:
    """One action on one item."""

    item_id: str
    kind: SignalKind
    at: datetime


@dataclass(frozen=True, slots=True)
class Contribution:
    """How much one feature of an item moves its rank."""

    feature: str
    points: int


def features(item: Item) -> tuple[str, ...]:
    """What an item is made of, as far as taste goes: source, author, category (and its parents) and tags."""
    found = [f"source:{s}" for s in item.sources]
    if item.author:
        found.append(f"author:{item.author.lower()}")
    found.extend(f"category:{path}" for path in (*ancestors(item.channel), item.channel))
    found.extend(
        f"tag:{t}"
        for t in dict.fromkeys((*item.feed_tags, *(item.enrichment.tags if item.enrichment else ())))
    )
    return tuple(found)


@dataclass(frozen=True, slots=True)
class Profile:
    """Feature weights learnt from signals. Empty until enough signals exist."""

    weights: dict[str, float]

    def contributions(self, item: Item) -> tuple[Contribution, ...]:
        """Per-feature points for an item, strongest first; features with no effect are left out."""
        parts = [Contribution(f, round(self.weights.get(f, 0.0) * POINTS_PER_UNIT)) for f in features(item)]
        return tuple(sorted((c for c in parts if c.points != 0), key=lambda c: -abs(c.points)))

    def boost(self, item: Item) -> int:
        """Total points added to the item's rank, bounded."""
        total = sum(c.points for c in self.contributions(item))
        return max(-MAX_BOOST, min(MAX_BOOST, total))


def learn(
    signals: Iterable[Signal],
    items: dict[str, Item],
    now: datetime,
    *,
    half_life_days: float,
    minimum: int,
) -> Profile:
    """Fold signals and ratings into weights, older ones counting less.

    Ratings live on the items, so changing or clearing one changes what is learnt. Below ``minimum`` signals
    and ratings together nothing is learnt.
    """
    signals = list(signals)
    rated = [
        (i, i.rated_at) for i in items.values() if i.rating is not Rating.NONE and i.rated_at is not None
    ]
    if len(signals) + len(rated) < minimum:
        return Profile({})
    weights: dict[str, float] = {}

    def learn_from(item: Item, strength: float, at: datetime) -> None:
        age_days = max((now - at).total_seconds() / 86400, 0.0)
        decayed = strength * math.pow(0.5, age_days / half_life_days)
        for feature in features(item):
            weights[feature] = weights.get(feature, 0.0) + decayed

    for signal in signals:
        if (item := items.get(signal.item_id)) is not None:
            learn_from(item, WEIGHTS[signal.kind], signal.at)
    for item, at in rated:
        learn_from(item, RATING_WEIGHT * int(item.rating), at)
    return Profile(weights)
