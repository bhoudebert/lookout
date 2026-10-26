"""Scenarios of openspec/specs/categories: one hierarchy, counted categories, filing existing items again."""

import json
import sqlite3
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
from tests.cli_support import FEED_URL, Lookout, reading
from tests.support import database, make_item
from tests.test_http import Api

from lookout.adapters.store import sqlite as store
from lookout.adapters.store.codec import decode, encode
from lookout.adapters.store.sqlite import SqliteItemRepository
from lookout.application.refile import Refile
from lookout.domain.channel import OTHER, Channel, ChannelCatalogue
from lookout.domain.item import Item


@pytest.fixture
def api(tmp_path: Path) -> Iterator[Api]:
    instance = Api(Lookout(tmp_path))
    yield instance
    instance.services.close()


def names(api: Api) -> list[str]:
    return [c["name"] for c in api.client.get("/api/taxonomy").json()["channels"]]


def categories(api: Api) -> dict[str, dict[str, Any]]:
    return {c["name"]: c for c in api.client.get("/api/taxonomy").json()["channels"]}


# --- the hierarchy ---


def test_a_nested_category_creates_its_parents(api: Api) -> None:
    created = api.client.post(
        "/api/channels", json={"name": "  Dev>  Rust > Async ", "description": " Futures "}
    )
    assert (created.status_code, created.json()["name"], created.json()["description"]) == (
        201,
        "Dev > Rust > Async",
        "Futures",
    )
    assert names(api) == [OTHER, "Dev", "Dev > Rust", "Dev > Rust > Async"]


def test_an_existing_parent_keeps_its_description_when_a_child_is_added(api: Api) -> None:
    api.client.post("/api/channels", json={"name": "Dev", "description": "Software"})
    api.client.post("/api/channels", json={"name": "Dev > Rust"})
    assert categories(api)["Dev"]["description"] == "Software"


@pytest.mark.parametrize(
    ("name", "status", "text"),
    [
        ("Dev >", 422, "none of them empty"),
        ("> Rust", 422, "none of them empty"),
        ("A > > B", 422, "none of them empty"),
        ("A > B > C > D > E", 422, "at most 4 levels"),
        ("x" * 41, 422, "at most 40 characters"),
        ("dev > rust", 409, "already exists"),
    ],
)
def test_bad_paths_are_refused_and_duplicates_ignore_case(
    api: Api, name: str, status: int, text: str
) -> None:
    api.client.post("/api/channels", json={"name": "Dev > Rust"})
    refused = api.client.post("/api/channels", json={"name": name})
    assert (refused.status_code, text in refused.json()["detail"]) == (status, True)


def test_a_category_with_subcategories_cannot_be_deleted_until_they_are_gone(api: Api) -> None:
    api.client.post("/api/channels", json={"name": "Dev > Rust"})
    refused = api.client.delete("/api/channels/dev")
    assert (refused.status_code, "has subcategories (Dev > Rust)" in refused.json()["detail"]) == (409, True)
    assert api.client.delete("/api/channels/Dev > Rust").status_code == 204
    assert api.client.delete("/api/channels/Dev").status_code == 204
    assert names(api) == [OTHER]


def test_a_source_feeding_a_parent_feeds_everything_under_it(tmp_path: Path) -> None:
    instance = Api(
        Lookout(
            tmp_path,
            channels=[{"name": "Dev > Rust"}, {"name": "Dev > Web"}, {"name": "AI"}],
            sources=[{"name": "blog", "type": "rss", "url": FEED_URL, "channels": ["Dev"]}],
        )
    )
    try:
        offered: list[bool] = []

        def answer(request: Any) -> str:
            system = request.content.decode()
            if "single emoji" in system:
                return json.dumps({"icon": "🧭"})
            offered.append("Dev > Web" in system and "AI:" not in system and "- AI" not in system)
            return reading(channel="Dev > Web")

        instance.lookout.network.chat = answer
        instance.run()
        assert set(offered) == {True}
        assert {i["channel"] for i in instance.items()} == {"Dev > Web"}
    finally:
        instance.services.close()


def test_a_source_feeding_one_leaf_or_one_branch_files_straight_there() -> None:
    catalogue = ChannelCatalogue(
        (Channel("Dev"), Channel("Dev > Rust"), Channel("Dev > Web")),
        {"leaf": ("Dev > Rust",), "branch": ("Dev",)},
    )
    assert catalogue.initial(("leaf",)) == "Dev > Rust"
    assert catalogue.initial(("branch",)) == "Dev"
    assert [c.name for c in catalogue.allowed(("branch",))] == ["Dev", "Dev > Rust", "Dev > Web"]
    assert [c.name for c in catalogue.children_of("dev")] == ["Dev > Rust", "Dev > Web"]
    assert catalogue.children_of("Dev > Rust") == ()


def test_a_source_may_name_a_category_by_any_spacing(api: Api) -> None:
    api.client.post("/api/channels", json={"name": "Dev > Rust"})
    created = api.client.post(
        "/api/sources",
        json={"name": "s", "type": "rss", "settings": {"url": FEED_URL}, "channels": ["dev>rust"]},
    )
    assert created.json()["channels"] == ["Dev > Rust"]


# --- counted categories ---


def test_each_category_says_how_many_items_it_holds_and_who_names_it(tmp_path: Path) -> None:
    instance = Api(
        Lookout(
            tmp_path,
            channels=[{"name": "Dev > Rust"}, {"name": "AI"}],
            sources=[{"name": "blog", "type": "rss", "url": FEED_URL, "channels": ["Dev > Rust"]}],
        )
    )
    try:
        instance.run()
        found = categories(instance)
        assert (found["Dev > Rust"]["items"], found["Dev > Rust"]["sources"]) == (3, ["blog"])
        assert (found["Dev"]["items"], found["Dev"]["sources"]) == (0, [])
        assert (found["AI"]["items"], found["AI"]["sources"]) == (0, [])
    finally:
        instance.services.close()


# --- moving a category ---


def move(api: Api, name: str, parent: str = "") -> Any:
    return api.client.post(f"/api/channels/{name}/move", json={"parent": parent})


def test_moving_a_category_takes_its_subcategories_its_items_and_its_sources_along(tmp_path: Path) -> None:
    instance = Api(
        Lookout(
            tmp_path,
            channels=[{"name": "Languages > Rust", "description": "Rust"}, {"name": "Dev"}, {"name": "AI"}],
            sources=[
                {"name": "blog", "type": "rss", "url": FEED_URL, "channels": ["Languages > Rust"]},
                {"name": "wide", "type": "rss", "url": FEED_URL + "?x", "channels": ["AI", "Languages"]},
            ],
        )
    )
    try:
        instance.run()
        moved = move(instance, "Languages", "Dev")
        assert (moved.status_code, moved.json()["name"]) == (200, "Dev > Languages")
        found = categories(instance)
        assert set(found) == {"Dev", "Dev > Languages", "Dev > Languages > Rust", "AI", OTHER}
        assert found["Dev > Languages > Rust"]["description"] == "Rust"
        assert found["Dev > Languages > Rust"]["items"] == 3
        assert found["Dev > Languages > Rust"]["sources"] == ["blog"]
        assert found["Dev > Languages"]["sources"] == ["wide"]
        assert {i["channel"] for i in instance.items(channel="Dev")} == {"Dev > Languages > Rust"}
        assert move(instance, "AI", "Dev").status_code == 200
        assert {i["channel"] for i in instance.items(channel="Dev")} == {"Dev > Languages > Rust"}
    finally:
        instance.services.close()


def test_a_database_with_a_path_but_not_its_parent_gets_the_parent_when_opened(tmp_path: Path) -> None:
    first = Api(Lookout(tmp_path, channels=[{"name": "Security"}]))
    first.services.close()
    raw = sqlite3.connect(tmp_path / "lookout.db")
    raw.execute("INSERT INTO channel_defs (name, description, position) VALUES ('Dev > Web', '', 99)")
    raw.commit()
    raw.close()
    reopened = Api(Lookout(tmp_path, channels=[{"name": "Security"}]))
    try:
        assert "Dev" in names(reopened)
        assert move(reopened, "Security", "Dev").json()["name"] == "Dev > Security"
    finally:
        reopened.services.close()


def test_moving_inside_a_parent_that_was_never_stored_is_refused_not_invented(api: Api) -> None:
    assert move(api, OTHER, "Ghost").status_code in (404, 409)
    assert "Ghost" not in names(api)


def test_a_category_can_go_back_to_the_top_level(api: Api) -> None:
    api.client.post("/api/channels", json={"name": "Dev > Rust"})
    assert move(api, "Dev > Rust").json()["name"] == "Rust"
    assert sorted(names(api)) == ["Dev", OTHER, "Rust"]


def test_moving_where_it_already_is_changes_nothing(api: Api) -> None:
    api.client.post("/api/channels", json={"name": "Dev > Rust"})
    assert move(api, "Dev > Rust", "Dev").json()["name"] == "Dev > Rust"
    assert sorted(names(api)) == ["Dev", "Dev > Rust", OTHER]


@pytest.mark.parametrize(
    ("name", "parent", "status"),
    [
        ("Nope", "", 404),
        ("Dev", "Nope", 404),
        (OTHER, "Dev", 409),
        ("Dev", "Dev > Rust", 422),
        ("Dev", "Dev", 422),
        ("Rust", "Dev", 409),
    ],
)
def test_impossible_moves_are_refused_and_change_nothing(
    api: Api, name: str, parent: str, status: int
) -> None:
    api.client.post("/api/channels", json={"name": "Dev > Rust"})
    api.client.post("/api/channels", json={"name": "Rust"})
    before = names(api)
    assert move(api, name, parent).status_code == status
    assert names(api) == before


def test_a_move_that_makes_the_path_too_deep_is_refused(api: Api) -> None:
    api.client.post("/api/channels", json={"name": "A > B > C > D"})
    api.client.post("/api/channels", json={"name": "X > Y"})
    assert move(api, "X", "A > B > C > D").status_code == 422


# --- tags carry what kinds used to ---


def test_what_an_item_is_comes_back_as_tags(api: Api) -> None:
    api.lookout.network.chat = lambda _r: reading(tags=["release", "python"])
    api.run()
    assert {tuple(i["tags"]) for i in api.items()} == {("release", "python")}


def test_a_database_with_kinds_keeps_them_as_tags_and_drops_the_columns(tmp_path: Path) -> None:
    path = tmp_path / "lookout.db"
    legacy = (
        '{"id": "k1", "url": "https://old.test/k", "title": "Old", "body": "", "published_at": '
        '"2026-10-20T08:00:00+00:00", "sources": ["blog"], "advisory": null, "enrichment": {"summary": "s", '
        '"kind": "release", "channel": "AI", "tags": ["a", "b", "c", "d", "e"], "score": 50, '
        '"action_needed": false, "reason": "r"}, "enrichment_failed": false, "stack_matches": [], '
        '"priority": 2, "priority_reason": "old", "state": "new", "snoozed_until": null, "starred": false, '
        '"boost": 0, "author": "", "channel": "AI", "feed_tags": [], "extra": {}}'
    )
    with sqlite3.connect(path) as db:
        for step in (store.migrate_v1, store.migrate_v2, store.migrate_v3, store.migrate_v4):
            step(db)
        db.execute("PRAGMA user_version = 4")
        db.execute(
            "INSERT INTO items (id, priority, state, starred, kind, channel, author, sources, search, rank, "
            "pending, published_at, snoozed_until, data) VALUES ('k1', 2, 'new', 0, 'release', 'AI', '', "
            "'|blog|', 'old', 50, 0, '2026-10-20T08:00:00+00:00', NULL, ?)",
            (legacy,),
        )
    repo = SqliteItemRepository(database(path))
    (item,) = repo.all()
    assert item.enrichment is not None
    assert item.enrichment.tags == ("a", "b", "c", "d", "e")  # already five: the kind does not overflow
    assert (tmp_path / "lookout.db.bak-v4").exists()
    with sqlite3.connect(path) as raw:
        columns = [row[1] for row in raw.execute("PRAGMA table_info(items)")]
        tables = [row[0] for row in raw.execute("SELECT name FROM sqlite_master WHERE type = 'table'")]
    assert "kind" not in columns
    assert "kind_defs" not in tables


def test_a_legacy_kind_becomes_a_tag_when_there_is_room() -> None:
    item = make_item(score=50)
    raw = encode(item).replace('"tags":[]', '"tags":["x"],"kind":"release"')
    assert decode(raw).enrichment is not None
    assert decode(raw).enrichment.tags == ("x", "release")  # type: ignore[union-attr]


# --- filing existing items again ---


def world(**routes: tuple[str, ...]) -> tuple[Refile, SqliteItemRepository]:
    items = SqliteItemRepository(database())
    catalogue = ChannelCatalogue((Channel("AI"), Channel("Dev"), Channel("Dev > Rust")), routes)
    return Refile(items, lambda: catalogue), items


def stored(items: SqliteItemRepository, item: Item) -> Item:
    found = items.get(item.id)
    assert found is not None
    return found


def test_an_item_whose_source_allows_one_category_is_filed_there_by_rule() -> None:
    refile, items = world(**{"rust-blog": ("Dev > Rust",)})
    item = make_item(sources=("rust-blog",), score=60)
    items.save(item)
    report = refile.run()
    moved = stored(items, item)
    assert (report.filed, report.queued) == (1, 0)
    assert moved.channel == "Dev > Rust"
    assert moved.enrichment is not None
    assert moved.enrichment.channel == "Dev > Rust"
    assert moved.priority == item.priority


def test_an_item_in_other_or_in_a_category_that_now_has_children_is_queued_for_the_model() -> None:
    refile, items = world()
    in_other = make_item("https://a.test/1", sources=("anywhere",), score=60)
    broad = make_item("https://a.test/2", sources=("anywhere",), score=60, channel="Dev")
    items.save(in_other)
    items.save(broad)
    report = refile.run()
    assert (report.filed, report.queued) == (0, 2)
    assert stored(items, in_other).enrichment is None
    assert stored(items, broad).enrichment_failed is False
    assert {i.id for i in items.pending_enrichment()} == {in_other.id, broad.id}


def test_an_unread_item_in_other_whose_source_names_a_branch_waits_in_it_not_in_other() -> None:
    refile, items = world(**{"deals": ("Dev",)})
    waiting = make_item("https://a.test/1", sources=("deals",))
    elsewhere = make_item("https://a.test/2", sources=("anywhere",))
    items.save(waiting)
    items.save(elsewhere)

    assert refile.run(dry_run=True).filed == 1
    assert stored(items, waiting).channel == OTHER
    report = refile.run()

    assert (report.filed, report.queued) == (1, 0)
    assert stored(items, waiting).channel == "Dev"
    assert stored(items, waiting).enrichment is None
    assert stored(items, elsewhere).channel == OTHER
    assert waiting.id in {i.id for i in items.pending_enrichment()}


def test_a_dry_run_says_what_would_happen_and_changes_nothing() -> None:
    refile, items = world(**{"rust-blog": ("Dev > Rust",)})
    rust = make_item("https://a.test/1", sources=("rust-blog",), score=60)
    other = make_item("https://a.test/2", sources=("anywhere",), score=60)
    items.save(rust)
    items.save(other)
    report = refile.run(dry_run=True)
    assert (report.filed, report.queued) == (1, 1)
    assert stored(items, rust) == rust
    assert stored(items, other) == other


def test_items_that_are_fine_are_left_alone() -> None:
    refile, items = world(**{"rust-blog": ("Dev > Rust",)})
    placed = make_item("https://a.test/1", sources=("rust-blog",), channel="Dev > Rust", score=60)
    deep = make_item("https://a.test/2", sources=("anywhere",), channel="Dev > Rust", score=60)
    elsewhere = make_item("https://a.test/3", sources=("anywhere",), channel="AI", score=60)
    unread = make_item("https://a.test/4", sources=("anywhere",))
    for item in (placed, deep, elsewhere, unread):
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

    api.client.post("/api/channels", json={"name": "Dev > Rust", "description": "The Rust language"})
    api.client.post("/api/channels", json={"name": "AI"})
    preview = api.client.post("/api/refile", params={"dry_run": "true"}).json()
    assert preview == {"filed": 0, "queued": 3}
    assert {i["unread"] for i in api.items()} == {False}
    assert api.client.post("/api/refile").json() == {"filed": 0, "queued": 3}
    assert {i["unread"] for i in api.items()} == {True}

    api.lookout.network.chat = lambda _r: reading(channel="Dev > Rust", score=92)
    api.run()
    assert {i["channel"] for i in api.items()} == {"Dev > Rust"}
    assert {i["priority"] for i in api.items()} == {"P0"}
    assert categories(api)["Dev > Rust"]["items"] == 3
    assert len(api.items(channel="Dev")) == 3


def test_a_source_that_now_names_one_leaf_files_its_items_without_the_model(api: Api) -> None:
    api.run()
    api.client.post("/api/channels", json={"name": "Dev > Rust"})
    api.client.put(
        "/api/sources/blog", json={"type": "rss", "settings": {"url": FEED_URL}, "channels": ["Dev > Rust"]}
    )
    assert api.client.post("/api/refile").json() == {"filed": 3, "queued": 0}
    assert {i["channel"] for i in api.items()} == {"Dev > Rust"}


def test_the_command_line_can_file_items_again_and_preview(tmp_path: Path) -> None:
    lookout = Lookout(tmp_path, channels=[{"name": "Dev > Rust"}])
    lookout.network.chat = lambda _r: reading(channel="Other")
    lookout("run")
    assert "would file 0 by rule, 3 queued for the model's next run" in lookout("refile", "--dry-run")
    assert "filed 0 by rule, 3 queued for the model's next run" in lookout("refile")
