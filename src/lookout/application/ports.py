"""Ports: what the application needs from the outside world."""

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

from lookout.domain.item import Item
from lookout.domain.priority import Priority
from lookout.domain.state import State


class Clock(Protocol):
    """The current time, always timezone-aware UTC."""

    def now(self) -> datetime: ...


@dataclass(frozen=True, slots=True)
class InboxQuery:
    """Filters of an item listing. ``None`` or empty means no filter."""

    priorities: frozenset[Priority] = frozenset()
    categories: frozenset[str] = frozenset()
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

    def all(self) -> tuple[Item, ...]: ...
