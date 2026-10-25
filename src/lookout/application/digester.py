"""Condense a selection of items into a digest (openspec: digest)."""

import hashlib
from dataclasses import dataclass, replace
from typing import Protocol

from lookout.application.ports import Clock, InboxQuery, ItemRepository
from lookout.domain.channel import OTHER, SEP
from lookout.domain.digest import Digest, Point, Section
from lookout.domain.item import Item

ITEM_CHARS = 600
"""What one item costs in the prompt, at most: the writer cuts titles and summaries to fit."""


class DigestError(Exception):
    """The model could not write the digest."""


class EmptyDigestError(Exception):
    """Nothing matches the selection."""


class DigestCancelledError(Exception):
    """The user stopped the digest."""


class DigestWatch(Protocol):
    """Who follows a digest being written: told how far it is, and asked whether to stop."""

    def planned(self, sections: int) -> None:
        """How many parts the digest has: its sections, then the headline."""
        ...

    def started(self, title: str) -> None:
        """Writing of this part begins."""
        ...

    def wrote(self, tokens: int) -> None:
        """The model wrote this many more tokens."""
        ...

    def stopped(self) -> bool:
        """Whether the user asked to stop."""
        ...


class Unwatched:
    """Nobody follows: never stops, remembers nothing."""

    def planned(self, sections: int) -> None: ...

    def started(self, title: str) -> None: ...

    def wrote(self, tokens: int) -> None: ...

    def stopped(self) -> bool:
        return False


class DigestWriter(Protocol):
    """Asks a model for the lines of a digest."""

    def write_section(self, title: str, items: tuple[Item, ...], watch: DigestWatch) -> tuple[Point, ...]:
        """Lines for these items, each citing items among them; raise ``DigestError`` or when stopped."""
        ...

    def write_headline(self, sections: tuple[Section, ...], watch: DigestWatch) -> str:
        """Two or three lines on what matters most across the sections; raise as above."""
        ...


class DigestRepository(Protocol):
    """Where digests are kept."""

    def save(self, digest: Digest) -> None: ...

    def get(self, digest_id: str) -> Digest | None: ...

    def recent(self, limit: int) -> tuple[Digest, ...]: ...

    def delete(self, digest_id: str) -> bool: ...


@dataclass(frozen=True, slots=True)
class DigestLimits:
    """How much one digest takes on."""

    max_items: int = 200
    context_chars: int = 40_000
    max_answer_tokens: int = 6144


class Digester:
    """Selects items like the inbox does, has the model write each category apart, then the headline."""

    def __init__(
        self,
        items: ItemRepository,
        writer: DigestWriter,
        digests: DigestRepository,
        clock: Clock,
        limits: DigestLimits = DigestLimits(),  # noqa: B008
    ) -> None:
        self._items = items
        self._writer = writer
        self._digests = digests
        self._clock = clock
        self._limits = limits

    def create(self, query: InboxQuery, scope: str, watch: DigestWatch = Unwatched()) -> Digest:  # noqa: B008
        """Write and keep a digest of the first items the query lists (the most urgent first).

        ``watch`` is told how far it is and may ask to stop, which raises ``DigestCancelledError``.
        """
        page = self._items.search(replace(query, limit=self._limits.max_items, offset=0))
        if not page.items:
            msg = "nothing matches this selection"
            raise EmptyDigestError(msg)
        groups = _by_category(page.items)
        watch.planned(len(groups) + 1)
        sections: list[Section] = []
        for title, group in groups:
            if watch.stopped():
                raise DigestCancelledError
            watch.started(title)
            points: list[Point] = []
            for chunk in _chunks(group, self._limits.context_chars):
                points.extend(self._writer.write_section(title, chunk, watch))
            if points:
                sections.append(Section(title, tuple(points)))
        if not sections:
            msg = "the model wrote nothing for this selection"
            raise DigestError(msg)
        if watch.stopped():
            raise DigestCancelledError
        watch.started("Headline")
        headline = self._writer.write_headline(tuple(sections), watch)
        now = self._clock.now()
        cited = {i for s in sections for p in s.points for i in p.items}
        digest = Digest(
            id=hashlib.sha256(f"{now.isoformat()}|{scope}".encode()).hexdigest()[:12],
            created_at=now,
            scope=scope,
            headline=headline,
            sections=tuple(sections),
            uncovered=tuple(i.id for i in page.items if i.id not in cited),
            total=page.total,
        )
        self._digests.save(digest)
        return digest


def _by_category(items: tuple[Item, ...]) -> list[tuple[str, tuple[Item, ...]]]:
    """Items grouped by their top category, in the order the first of each appears, Other last."""
    groups: dict[str, list[Item]] = {}
    for item in items:
        groups.setdefault(item.channel.split(SEP)[0], []).append(item)
    ordered = sorted(groups.items(), key=lambda kv: kv[0].lower() == OTHER.lower())
    return [(title, tuple(group)) for title, group in ordered]


def _chunks(items: tuple[Item, ...], budget: int) -> list[tuple[Item, ...]]:
    """Consecutive items, each chunk costing at most ``budget`` characters (at least one item)."""
    chunks: list[list[Item]] = [[]]
    used = 0
    for item in items:
        cost = min(len(item.title) + len(_text(item)), ITEM_CHARS)
        if chunks[-1] and used + cost > budget:
            chunks.append([])
            used = 0
        chunks[-1].append(item)
        used += cost
    return [tuple(c) for c in chunks]


def _text(item: Item) -> str:
    """What the model reads of an item: its own summary, else the start of the feed text."""
    return item.enrichment.summary if item.enrichment else item.body
