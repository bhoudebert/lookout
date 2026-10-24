"""Scenarios of openspec/specs/categories: managed kinds, filing items again, counted categories."""

import sqlite3
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
from tests.cli_support import FEED_URL, Lookout, reading
from tests.support import database, make_item
from tests.test_http import Api

from lookout.adapters.store import sqlite as store
from lookout.adapters.store.sqlite import SqliteItemRepository
from lookout.application.refile import Refile
from lookout.domain.channel import OTHER, Channel, ChannelCatalogue
from lookout.domain.item import Item


@pytest.fixture
def api(tmp_path: Path) -> Iterator[Api]:
    instance = Api(Lookout(tmp_path))
    yield instance
    instance.services.close()


def kinds(api: Api) -> list[str]:
    return api.client.get("/api/taxonomy").json()["kinds"]


def categories(api: Api) -> dict[str, dict[str, Any]]:
    return {c["name"]: c for c in api.client.get("/api/taxonomy").json()["channels"]}


# --- kinds ------------------------------------------------------------------------------------------------


def test_the_kinds_of_the_file_are_seeded_and_other_always_exists(tmp_path: Path) -> None:
    instance = Api(Lookout(tmp_path, kinds=["release", "schedule"]))
    try:
        assert kinds(instance) == ["release", "schedule", "other"]
    finally:
        instance.services.close()


def test_a_kind_can_be_added_normalised_and_removed(api: Api) -> None:
    created = api.client.post("/api/kinds", json={"name": "  Weekly   DIGEST "})
    assert (created.status_code, created.json()) == (201, "weekly digest")
    assert "weekly digest" in kinds(api)
    assert api.client.delete("/api/kinds/Weekly Digest").status_code == 204
    assert "weekly digest" not in kinds(api)


@pytest.mark.parametrize(
    ("method", "path", "body", "status", "text"),
    [
        ("post", "/api/kinds", {"name": "RELEASE"}, 409, "already exists"),
        ("post", "/api/kinds", {"name": "   "}, 422, "needs a name"),
        ("post", "/api/kinds", {"name": "x" * 41}, 422, "1 to 40"),
        ("delete", "/api/kinds/ghost", None, 404, "ghost"),
        ("delete", "/api/kinds/OTHER", None, 409, "always exists"),
    ],
)
def test_kinds_are_protected(api: Api, method: str, path: str, body: Any, status: int, text: str) -> None:
    response = api.client.post(path, json=body) if method == "post" else api.client.delete(path)
    assert response.status_code == status
    assert text in response.json()["detail"]


def test_the_model_chooses_among_the_kinds_as_they_are_now(api: Api) -> None:
    api.client.post("/api/kinds", json={"name": "weekly digest"})
    api.lookout.network.chat = lambda _r: reading(kind="Weekly Digest")
    api.run()
    assert {i["kind"] for i in api.items()} == {"weekly digest"}


def test_a_database_that_was_already_seeded_still_gets_its_kinds_from_the_file(tmp_path: Path) -> None:
    path = tmp_path / "lookout.db"
    with sqlite3.connect(path) as db:
        for step in (store.migrate_v1, store.migrate_v2, store.migrate_v3):
            step(db)
        db.execute("PRAGMA user_version = 3")
        db.execute("INSERT INTO flags (name) VALUES ('seeded')")
        db.execute("INSERT INTO channel_defs (name, description, position) VALUES ('Other', '', 1)")
    instance = Api(Lookout(tmp_path, kinds=["release", "security"]))
    try:
        assert kinds(instance) == ["release", "security", "other"]
        assert (tmp_path / "lookout.db.bak-v3").exists()
    finally:
        instance.services.close()


# --- categories with their counts -----------------------------------------------------------------------


def test_each_category_says_how_many_items_it_holds_and_who_feeds_it(tmp_path: Path) -> None:
    instance = Api(
        Lookout(
            tmp_path,
            channels=[{"name": "Rust"}, {"name": "AI"}],
            sources=[{"name": "blog", "type": "rss", "url": FEED_URL, "channels": ["Rust"]}],
        )
    )
    try:
        instance.run()
        found = categories(instance)
        assert (found["Rust"]["items"], found["Rust"]["sources"]) == (3, ["blog"])
        assert (found["AI"]["items"], found["AI"]["sources"]) == (0, [])
        assert (found[OTHER]["items"], found[OTHER]["sources"]) == (0, [])
    finally:
        instance.services.close()


# --- filing existing items again ------------------------------------------------------------------------


def world(**routes: tuple[str, ...]) -> tuple[Refile, SqliteItemRepository]:
    items = SqliteItemRepository(database())
    catalogue = ChannelCatalogue((Channel("AI"), Channel("Rust")), routes)
    return Refile(items, lambda: catalogue), items


def stored(items: SqliteItemRepository, item: Item) -> Item:
    found = items.get(item.id)
    assert found is not None
    return found


def test_an_item_whose_source_allows_one_category_is_filed_there_by_rule() -> None:
    refile, items = world(**{"rust-blog": ("Rust",)})
    item = make_item(sources=("rust-blog",), score=60)
    items.save(item)
    report = refile.run()
    moved = stored(items, item)
    assert (report.filed, report.queued) == (1, 0)
    assert (moved.channel, moved.enrichment.channel if moved.enrichment else None) == ("Rust", "Rust")
    assert moved.enrichment is not None
    assert moved.priority == item.priority


def test_an_item_in_other_whose_sources_allow_several_is_queued_for_the_model() -> None:
    refile, items = world()
    read = make_item(sources=("anywhere",), score=60)
    items.save(read)
    report = refile.run()
    again = stored(items, read)
    assert (report.filed, report.queued) == (0, 1)
    assert again.enrichment is None
    assert again.enrichment_failed is False
    assert [i.id for i in items.pending_enrichment()] == [read.id]


def test_items_that_are_fine_are_left_alone() -> None:
    refile, items = world(**{"rust-blog": ("Rust",)})
    placed = make_item("https://a.test/1", sources=("rust-blog",), channel="Rust", score=60)
    elsewhere = make_item("https://a.test/2", sources=("anywhere",), channel="AI", score=60)
    unread = make_item("https://a.test/3", sources=("anywhere",))
    for item in (placed, elsewhere, unread):
        items.save(item)
    assert (refile.run().filed, refile.run().queued) == (0, 0)
    assert stored(items, elsewhere) == elsewhere


def test_when_only_other_exists_nothing_moves() -> None:
    items = SqliteItemRepository(database())
    refile = Refile(items, ChannelCatalogue)
    items.save(make_item(score=60))
    assert (refile.run().filed, refile.run().queued) == (0, 0)


def test_adding_categories_then_filing_again_then_running_files_what_is_already_in_the_inbox(
    api: Api,
) -> None:
    api.run()
    assert {i["channel"] for i in api.items()} == {OTHER}

    api.client.post("/api/channels", json={"name": "Rust", "description": "The Rust language"})
    api.client.post("/api/channels", json={"name": "AI"})
    report = api.client.post("/api/refile").json()
    assert report == {"filed": 0, "queued": 3}
    assert {i["unread"] for i in api.items()} == {True}

    api.lookout.network.chat = lambda _r: reading(channel="Rust", score=92)
    api.run()
    assert {i["channel"] for i in api.items()} == {"Rust"}
    assert {i["priority"] for i in api.items()} == {"P0"}
    assert categories(api)["Rust"]["items"] == 3


def test_a_source_that_now_names_one_category_files_its_items_without_the_model(api: Api) -> None:
    api.run()
    api.client.post("/api/channels", json={"name": "Rust"})
    api.client.put(
        "/api/sources/blog", json={"type": "rss", "settings": {"url": FEED_URL}, "channels": ["Rust"]}
    )
    assert api.client.post("/api/refile").json() == {"filed": 3, "queued": 0}
    assert {i["channel"] for i in api.items()} == {"Rust"}


def test_the_command_line_can_file_items_again(tmp_path: Path) -> None:
    lookout = Lookout(tmp_path, channels=[{"name": "Rust"}])
    lookout.network.chat = lambda _r: reading(channel="Other")
    lookout("run")
    assert "filed 0 by rule, 3 queued for the model's next run" in lookout("refile")
