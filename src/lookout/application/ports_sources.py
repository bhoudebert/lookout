"""Ports of the pipeline: sources, the model, and the bookkeeping around runs."""

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

from lookout.domain.channel import Channel
from lookout.domain.enrichment import Enrichment
from lookout.domain.item import Item
from lookout.domain.profile import Example
from lookout.domain.raw import RawItem


class SourceError(Exception):
    """A source could not be read."""


class EnrichmentError(Exception):
    """The model gave no usable answer."""


class SourceFetcher(Protocol):
    """Reads one configured source."""

    @property
    def name(self) -> str: ...

    def fetch(self) -> tuple[RawItem, ...]:
        """Return the current entries, or raise ``SourceError``."""
        ...


class Enricher(Protocol):
    """Asks a model to read one item."""

    def enrich(
        self, item: Item, channels: tuple[Channel, ...], examples: tuple[Example, ...] = ()
    ) -> Enrichment:
        """Return a validated reading, with the channel among ``channels``, or raise ``EnrichmentError``.

        ``examples`` are items the user rated, as a sample of taste.
        """
        ...


class IconSuggester(Protocol):
    """Asks a model for the icon of a category."""

    def suggest_icon(self, channel: Channel) -> str:
        """Return one emoji (possibly empty when the model has none), or raise ``EnrichmentError``."""
        ...


@dataclass(frozen=True, slots=True)
class SourceStatus:
    """How a source did the last time."""

    name: str
    last_run: datetime | None = None
    last_error: str | None = None
    failures: int = 0
    next_attempt: datetime | None = None
    items_seen: int = 0


class SourceStatusRepository(Protocol):
    """Keeps the health of sources."""

    def get(self, name: str) -> SourceStatus: ...

    def save(self, status: SourceStatus) -> None: ...


class UsageRepository(Protocol):
    """Counts model calls per UTC day."""

    def calls_on(self, day: str) -> int: ...

    def record_call(self, day: str) -> None: ...
