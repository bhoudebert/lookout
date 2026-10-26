"""A digest: many items condensed into a few cited lines, grouped by category (openspec: digest)."""

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class Point:
    """One line of a digest and the items it was written from."""

    text: str
    items: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class Section:
    """The points of one category."""

    title: str
    points: tuple[Point, ...]


@dataclass(frozen=True, slots=True)
class Digest:
    """What the model wrote about a selection. ``uncovered`` are the selected items no point cites."""

    id: str
    created_at: datetime
    scope: str
    headline: str
    sections: tuple[Section, ...]
    uncovered: tuple[str, ...]
    total: int
    """How many items matched the selection; the digest covers the first ``len(cited) + len(uncovered)``."""
    since: datetime | None = None
    until: datetime | None = None
    """When its oldest and newest items were published; ``None`` for digests kept before this was recorded."""

    @property
    def cited(self) -> tuple[str, ...]:
        """The items some point cites, once each, in the order of the digest."""
        return tuple(dict.fromkeys(i for s in self.sections for p in s.points for i in p.items))

    @property
    def count(self) -> int:
        """How many items the model was given."""
        return len(self.cited) + len(self.uncovered)
