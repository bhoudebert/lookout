"""Fakes and builders shared by the scenario tests."""

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path

from lookout.adapters.store.sqlite import Database, SqliteItemRepository, SqliteSignalRepository
from lookout.application.personalize import Personalize
from lookout.application.ports_sources import EnrichmentError, SourceError
from lookout.application.triage import Triage
from lookout.domain.advisory import Advisory
from lookout.domain.enrichment import Enrichment
from lookout.domain.item import Item, item_id
from lookout.domain.priority import Priority
from lookout.domain.raw import RawItem

NOW = datetime(2026, 10, 24, 9, 0, tzinfo=UTC)


@dataclass
class FixedClock:
    """A clock the test moves by hand."""

    moment: datetime = NOW

    def now(self) -> datetime:
        return self.moment

    def advance(self, **delta: float) -> None:
        self.moment += timedelta(**delta)


def enrichment(
    score: int = 50, category: str = "tooling", tags: tuple[str, ...] = (), summary: str = "s"
) -> Enrichment:
    return Enrichment(
        summary=summary, category=category, tags=tags, score=score, action_needed=False, reason="because"
    )


def make_item(
    url: str = "https://example.com/post",
    *,
    title: str = "A post",
    body: str = "",
    sources: tuple[str, ...] = ("blog",),
    priority: Priority = Priority.P2,
    advisory: Advisory | None = None,
    score: int | None = None,
    category: str = "tooling",
    published_at: datetime = NOW,
) -> Item:
    item = Item(
        id=item_id(url),
        url=url,
        title=title,
        body=body,
        published_at=published_at,
        sources=sources,
        advisory=advisory,
        priority=priority,
    )
    return item.enriched(enrichment(score, category)) if score is not None else item


_OPENED: list[Database] = []


def database(path: Path | str = ":memory:") -> Database:
    """A database the test does not have to close: conftest closes every one after the test."""
    db = Database(path)
    _OPENED.append(db)
    return db


def repository(path: Path | str = ":memory:") -> SqliteItemRepository:
    return SqliteItemRepository(database(path))


def close_repositories() -> None:
    while _OPENED:
        _OPENED.pop().close()


class FakeFetcher:
    """A source that returns the given entries, or fails with the given message."""

    def __init__(self, name: str, raws: tuple[RawItem, ...] = (), error: str | None = None) -> None:
        self.name = name
        self.raws = raws
        self.error = error
        self.calls = 0

    def fetch(self) -> tuple[RawItem, ...]:
        self.calls += 1
        if self.error is not None:
            raise SourceError(self.error)
        return self.raws


class ScriptedEnricher:
    """Answers items by title from a table; anything not listed gets a default reading."""

    def __init__(self, answers: dict[str, Enrichment | EnrichmentError] | None = None) -> None:
        self.answers = answers or {}
        self.asked: list[str] = []

    def enrich(self, item: Item) -> Enrichment:
        self.asked.append(item.title)
        answer = self.answers.get(item.title, enrichment(50))
        if isinstance(answer, EnrichmentError):
            raise answer
        return answer


def raw(
    url: str = "https://example.com/post",
    *,
    source: str = "blog",
    title: str = "A post",
    body: str = "",
    published_at: datetime | None = NOW,
    advisory: Advisory | None = None,
) -> RawItem:
    return RawItem(source, url, title, body, published_at, advisory)


def triage_for(
    repo: SqliteItemRepository, db: Database, clock: FixedClock | None = None
) -> tuple[Triage, Personalize]:
    """A triage use case wired to real personalization on the same database."""
    personalize = Personalize(repo, SqliteSignalRepository(db), clock or FixedClock())
    return Triage(repo, personalize), personalize
