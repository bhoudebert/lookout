"""What the user's actions teach (openspec: personalization). Orders items inside a priority band."""

import math
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

from lookout.domain.item import Item

MAX_BOOST = 20
POINTS_PER_UNIT = 4


class SignalKind(StrEnum):
    """Things the user does that say something about taste."""

    OPEN = "open"
    STAR = "star"
    DONE = "done"
    DISMISS = "dismiss"
    SNOOZE = "snooze"


WEIGHTS: dict[SignalKind, float] = {
    SignalKind.STAR: 3.0,
    SignalKind.DONE: 3.0,
    SignalKind.OPEN: 1.0,
    SignalKind.SNOOZE: 0.0,
    SignalKind.DISMISS: -2.0,
}


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
    """What an item is made of, as far as taste goes: source, author, channel, kind and tags."""
    found = [f"source:{s}" for s in item.sources]
    if item.author:
        found.append(f"author:{item.author.lower()}")
    found.append(f"channel:{item.channel}")
    if item.enrichment is not None:
        found.append(f"kind:{item.enrichment.kind}")
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
    """Fold signals into weights, older ones counting less. Below ``minimum`` signals nothing is learnt."""
    signals = list(signals)
    if len(signals) < minimum:
        return Profile({})
    weights: dict[str, float] = {}
    for signal in signals:
        item = items.get(signal.item_id)
        if item is None:
            continue
        age_days = max((now - signal.at).total_seconds() / 86400, 0.0)
        strength = WEIGHTS[signal.kind] * math.pow(0.5, age_days / half_life_days)
        for feature in features(item):
            weights[feature] = weights.get(feature, 0.0) + strength
    return Profile(weights)
