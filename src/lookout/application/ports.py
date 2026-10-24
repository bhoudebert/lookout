"""Ports: what the application needs from the outside world."""

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

from lookout.domain.item import Item
from lookout.domain.priority import Priority
from lookout.domain.profile import Signal, SignalKind
from lookout.domain.state import State


class Clock(Protocol):
    """The current time, always timezone-aware UTC."""

    def now(self) -> datetime: ...


@dataclass(frozen=True, slots=True)
class InboxQuery:
    """Filters of an item listing. ``None`` or empty means no filter."""

    priorities: frozenset[Priority] = frozenset()
    kinds: frozenset[str] = frozenset()
    channels: frozenset[str] = frozenset()
    sources: frozenset[str] = frozenset()
    states: frozenset[State] = frozenset()
    starred: bool | None = None
    text: str = ""
    limit: int = 50
    offset: int = 0


@dataclass(frozen=True, slots=True)
class Page:
    """A page of items and the total matching the query."""

    items: tuple[Item, ...]
    total: int


class ItemRepository(Protocol):
    """Persistence of items."""

    def get(self, item_id: str) -> Item | None: ...

    def save(self, item: Item) -> None: ...

    def search(self, query: InboxQuery) -> Page: ...

    def snoozed_before(self, moment: datetime) -> tuple[Item, ...]: ...

    def pending_enrichment(self) -> tuple[Item, ...]: ...

    def count_by_channel(self) -> dict[str, int]: ...

    def all(self) -> tuple[Item, ...]: ...


class SignalRepository(Protocol):
    """What the user did."""

    def add(self, signal: Signal) -> None: ...

    def all(self) -> tuple[Signal, ...]: ...

    def clear(self) -> None: ...


class Feedback(Protocol):
    """Told about every action that says something about taste."""

    def record(self, item: Item, kind: SignalKind) -> None: ...
