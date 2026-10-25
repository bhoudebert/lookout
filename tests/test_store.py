"""The SQLite store: round trips, filters, ordering, migrations (openspec: triage inbox query, ADR 0004)."""

import sqlite3
import threading
from datetime import timedelta
from pathlib import Path

import pytest
from tests.support import NOW, database, make_item, repository

from lookout.adapters.store import sqlite as store
from lookout.adapters.store.sqlite import SchemaTooNewError, SqliteItemRepository
from lookout.application.ports import InboxQuery
from lookout.domain.advisory import Advisory
from lookout.domain.priority import Priority
from lookout.domain.severity import Severity
from lookout.domain.state import State


def test_item_survives_a_round_trip_with_everything_attached() -> None:
    repo = repository()
    advisory = Advisory(
        Severity.HIGH, "django", "pypi", known_exploited=True, identifiers=("CVE-1", "GHSA-2")
    )
    item = (
        make_item(advisory=advisory, score=80)
        .assessed(Priority.P1, "why", ("django",))
        .snooze(NOW + timedelta(days=1))
        .star()
    )
    repo.save(item)
    assert repo.get(item.id) == item


def test_unknown_id_is_none() -> None:
    assert repository().get("missing") is None


def test_saving_twice_replaces() -> None:
    repo = repository()
    item = make_item()
    repo.save(item)
    repo.save(item.mark_done())
    assert [i.state for i in repo.all()] == [State.DONE]


def test_inbox_orders_by_priority_then_score_then_recency() -> None:
    repo = repository()
    old = make_item(
        "https://a.test/old", priority=Priority.P1, score=50, published_at=NOW - timedelta(days=2)
    )
    new = make_item("https://a.test/new", priority=Priority.P1, score=50)
    high = make_item(
        "https://a.test/high", priority=Priority.P1, score=60, published_at=NOW - timedelta(days=9)
    )
    urgent = make_item("https://a.test/urgent", priority=Priority.P0, score=1)
    for item in (old, new, high, urgent):
        repo.save(item)
    assert [i.id for i in repo.search(InboxQuery()).items] == [urgent.id, high.id, new.id, old.id]


def test_filters_combine() -> None:
    repo = repository()
    a = make_item(
        "https://a.test/a",
        title="Django 6 released",
        sources=("hn", "blog"),
        priority=Priority.P1,
        channel="Dev > Web",
        score=70,
    )
    b = make_item(
        "https://a.test/b",
        title="Rust news",
        sources=("reddit",),
        priority=Priority.P2,
        channel="Dev > Rust",
        score=70,
    ).star()
    c = make_item("https://a.test/c", title="Other", sources=("hn",), priority=Priority.P3).mark_done()
    for item in (a, b, c):
        repo.save(item)

    def ids(**kw: object) -> set[str]:
        return {i.id for i in repo.search(InboxQuery(**kw)).items}  # type: ignore[arg-type]

    assert ids(priorities=frozenset({Priority.P1})) == {a.id}
    assert ids(channels=frozenset({"Dev > Rust"})) == {b.id}
    assert ids(channels=frozenset({"Dev"})) == {a.id, b.id}
    assert ids(channels=frozenset({"Dev > Web", "Other"})) == {a.id, c.id}
    assert ids(channels=frozenset({"Dev > Rus"})) == set()
    assert ids(channels=frozenset({"Developers"})) == set()
    assert ids(sources=frozenset({"hn"})) == {a.id, c.id}
    assert ids(sources=frozenset({"reddit", "blog"})) == {a.id, b.id}
    assert ids(states=frozenset({State.DONE})) == {c.id}
    assert ids(starred=True) == {b.id}
    assert ids(starred=False) == {a.id, c.id}
    assert ids(text="DJANGO") == {a.id}
    assert ids(sources=frozenset({"hn"}), states=frozenset({State.NEW})) == {a.id}


def test_pagination_reports_the_total() -> None:
    repo = repository()
    for n in range(5):
        repo.save(make_item(f"https://a.test/{n}", published_at=NOW - timedelta(hours=n)))
    page = repo.search(InboxQuery(limit=2, offset=2))
    assert (len(page.items), page.total) == (2, 5)


def test_new_database_gets_the_current_schema(tmp_path: Path) -> None:
    path = tmp_path / "lookout.db"
    repository(path)
    with sqlite3.connect(path) as db:
        assert db.execute("PRAGMA user_version").fetchone()[0] == len(store.MIGRATIONS)
    assert list(tmp_path.glob("*.bak-*")) == []


def test_reopening_a_current_database_changes_nothing(tmp_path: Path) -> None:
    path = tmp_path / "lookout.db"
    repository(path).save(make_item())
    assert len(repository(path).all()) == 1


def test_database_from_a_newer_lookout_is_refused_and_left_alone(tmp_path: Path) -> None:
    path = tmp_path / "lookout.db"
    with sqlite3.connect(path) as db:
        db.execute("PRAGMA user_version = 99")
    with pytest.raises(SchemaTooNewError, match="99"):
        repository(path)
    with sqlite3.connect(path) as db:
        assert db.execute("PRAGMA user_version").fetchone()[0] == 99


def add_column(db: sqlite3.Connection) -> None:
    db.execute("ALTER TABLE items ADD COLUMN extra TEXT")


def test_pending_migration_runs_after_a_backup(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    path = tmp_path / "lookout.db"
    first = database(path)
    SqliteItemRepository(first).save(make_item())
    first.close()
    monkeypatch.setattr(store, "MIGRATIONS", (*store.MIGRATIONS, add_column))
    upgraded = repository(path)
    assert len(upgraded.all()) == 1
    assert (tmp_path / f"lookout.db.bak-v{len(store.MIGRATIONS) - 1}").exists()


def test_failing_migration_leaves_the_database_unchanged(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = tmp_path / "lookout.db"
    repository(path)

    def broken(db: sqlite3.Connection) -> None:
        db.execute("ALTER TABLE items ADD COLUMN half_done TEXT")
        msg = "boom"
        raise RuntimeError(msg)

    monkeypatch.setattr(store, "MIGRATIONS", (*store.MIGRATIONS, broken))
    with pytest.raises(RuntimeError, match="boom"):
        repository(path)
    with sqlite3.connect(path) as db:
        assert db.execute("PRAGMA user_version").fetchone()[0] == len(store.MIGRATIONS) - 1
        assert "half_done" not in [row[1] for row in db.execute("PRAGMA table_info(items)")]


def test_threads_can_share_one_database(tmp_path: Path) -> None:
    """Requests arrive on several threads while a run writes; nothing may collide (a journey found this)."""
    repo = repository(tmp_path / "shared.db")
    items = [make_item(f"https://a.test/{n}", title=f"Item {n}") for n in range(20)]
    for item in items:
        repo.save(item)
    errors: list[BaseException] = []

    def work(offset: int) -> None:
        try:
            for round_ in range(60):
                item = items[(offset + round_) % len(items)]
                repo.save(item.star())
                assert repo.get(item.id) is not None
                repo.search(InboxQuery(text="item"))
        except BaseException as error:
            errors.append(error)

    threads = [threading.Thread(target=work, args=(n,)) for n in range(8)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    assert errors == []


LEGACY_ITEM = (
    '{"id": "legacy1", "url": "https://old.test/a", "title": "Old item", "body": "", '
    '"published_at": "2026-10-20T08:00:00+00:00", "sources": ["blog"], "advisory": null, '
    '"enrichment": {"summary": "s", "category": "release", "tags": ["x"], "score": 60, '
    '"action_needed": false, "reason": "r"}, "enrichment_failed": false, "stack_matches": [], '
    '"priority": 2, "priority_reason": "old", '
    '"state": "seen", "snoozed_until": null, "starred": true, "boost": 3, "extra": {}}'
)


def test_a_database_from_before_channels_keeps_every_item(tmp_path: Path) -> None:
    """Existing data: the old category is kept as a tag, the channel is Other, no author."""
    path = tmp_path / "lookout.db"
    with sqlite3.connect(path) as db:
        store.migrate_v1(db)
        db.execute("PRAGMA user_version = 1")
        db.execute(
            "INSERT INTO items (id, priority, state, starred, category, sources, search, rank, pending, "
            "published_at, snoozed_until, data) "
            "VALUES ('legacy1', 2, 'seen', 1, 'release', '|blog|', 'old item', 63, 0, "
            "'2026-10-20T08:00:00+00:00', NULL, ?)",
            (LEGACY_ITEM,),
        )
    repo = repository(path)
    (item,) = repo.all()
    assert (item.id, item.channel, item.author, item.feed_tags) == ("legacy1", "Other", "", ())
    assert item.enrichment is not None
    assert (item.enrichment.tags, item.enrichment.channel, item.starred, item.boost) == (
        ("x", "release"),
        "Other",
        True,
        3,
    )
    assert [i.id for i in repo.search(InboxQuery(text="old")).items] == ["legacy1"]
    assert (tmp_path / "lookout.db.bak-v1").exists()
    repo.save(item)
    assert repo.get("legacy1") == item


def test_percent_and_underscore_in_names_and_text_are_not_wildcards() -> None:
    repo = repository()
    a = make_item("https://a.test/a", title="100% sure", sources=("a_b",))
    b = make_item("https://a.test/b", title="1000 sure", sources=("aXb",))
    repo.save(a)
    repo.save(b)

    def ids(**kw: object) -> set[str]:
        return {i.id for i in repo.search(InboxQuery(**kw)).items}  # type: ignore[arg-type]

    assert ids(sources=frozenset({"a_b"})) == {a.id}
    assert ids(sources=frozenset({"a%"})) == set()
    assert ids(text="100%") == {a.id}
    assert ids(text="10_0") == set()
