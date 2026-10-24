"""Fakes and builders shared by the scenario tests."""

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path

from lookout.adapters.store.sqlite import SqliteItemRepository
from lookout.domain.advisory import Advisory
from lookout.domain.enrichment import Enrichment
from lookout.domain.item import Item, item_id
from lookout.domain.priority import Priority

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


_OPENED: list[SqliteItemRepository] = []


def repository(path: Path | str = ":memory:") -> SqliteItemRepository:
    """A repository the test does not have to close: conftest closes every one after the test."""
    repo = SqliteItemRepository(path)
    _OPENED.append(repo)
    return repo


def close_repositories() -> None:
    while _OPENED:
        _OPENED.pop().close()
