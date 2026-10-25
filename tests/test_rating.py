"""Scenarios of openspec/specs/triage (Rating) and personalization: thumbs teach, done clears (ADR 0017)."""

import json
import sqlite3
from datetime import timedelta
from pathlib import Path
from typing import Any

import pytest
from tests.cli_support import Lookout
from tests.support import NOW, database, make_item
from tests.test_http import Api
from tests.test_personalization import World

from lookout.adapters.store import sqlite as store
from lookout.adapters.store.codec import encode
from lookout.adapters.store.sqlite import SqliteItemRepository, SqliteSignalRepository
from lookout.application.triage import Action, Undo
from lookout.domain.profile import SignalKind, learn
from lookout.domain.rating import Rating
from lookout.domain.state import State

# --- the item ---


def test_a_thumb_sets_the_rating_and_the_same_thumb_again_clears_it() -> None:
    item = make_item()
    up = item.rated(Rating.UP, NOW)
    assert (up.rating, up.rated_at) == (Rating.UP, NOW)
    assert up.rated(Rating.UP, NOW).rating is Rating.NONE
    assert up.rated(Rating.UP, NOW).rated_at is None
    down = up.rated(Rating.DOWN, NOW + timedelta(hours=1))
    assert (down.rating, down.rated_at) == (Rating.DOWN, NOW + timedelta(hours=1))
    assert down.rated(Rating.NONE, NOW).rating is Rating.NONE
    assert down.rated(Rating.NONE, NOW).rated_at is None


# --- the use case and what is learnt ---


def test_rating_leaves_the_item_in_the_inbox_and_done_removes_it_without_teaching() -> None:
    world = World(minimum=1)
    item = world.add(1, source="s", channel="c")
    world.triage.rate(item.id, Rating.DOWN)
    assert world.stored(item).state is State.NEW
    assert world.stored(item).rating is Rating.DOWN
    world.triage.act(item.id, Action.DONE)
    assert world.stored(item).state is State.DONE
    assert (
        world.stored(item).rating is Rating.DOWN
    )  # still rated: the thumb is about taste, not about the inbox
    assert world.signals.all() == ()
    assert world.personalize.profile().weights["source:s"] < 0


def test_thumbs_up_and_down_push_later_items_up_and_down() -> None:
    world = World(minimum=3)
    for n in range(3):
        world.triage.rate(world.add(n, source="liked", channel="gold").id, Rating.UP)
        world.triage.rate(world.add(n + 10, source="noisy", channel="junk").id, Rating.DOWN)
    liked = world.add(20, source="liked", channel="gold")
    noisy = world.add(21, source="noisy", channel="junk")
    world.personalize.rerank()
    assert world.stored(liked).boost > 0 > world.stored(noisy).boost


def test_clearing_a_rating_changes_what_is_learnt() -> None:
    world = World(minimum=1)
    item = world.add(1, source="s", channel="c")
    world.triage.rate(item.id, Rating.UP)
    assert world.personalize.profile().weights["source:s"] == pytest.approx(3.0)
    world.triage.rate(item.id, Rating.UP)
    assert world.personalize.profile().weights == {}


def test_an_old_rating_counts_less_and_ratings_count_towards_the_minimum() -> None:
    world = World(minimum=2, half_life=10.0)
    world.triage.rate(world.add(1, source="s", channel="c").id, Rating.UP)
    assert world.personalize.profile().weights == {}  # one rating is below the minimum of two
    world.triage.rate(world.add(2, source="s", channel="c").id, Rating.UP)
    fresh = world.personalize.profile().weights["source:s"]
    world.clock.advance(days=10)
    assert world.personalize.profile().weights["source:s"] == pytest.approx(fresh / 2)


def test_a_rating_of_an_item_that_is_gone_or_has_no_time_is_ignored() -> None:
    odd = make_item()
    odd = odd.restored(State.NEW, None, starred=False, rating=Rating.UP, rated_at=None)
    assert learn([], {odd.id: odd}, NOW, half_life_days=30, minimum=1).weights == {}


def test_undoing_a_rating_puts_back_the_old_one() -> None:
    world = World(minimum=1)
    item = world.add(1, source="s", channel="c")
    outcome = world.triage.rate(item.id, Rating.DOWN)
    world.triage.undo(outcome)
    assert world.stored(item).rating is Rating.NONE
    assert world.personalize.profile().weights == {}


def test_a_client_can_put_ratings_back_as_they_were() -> None:
    world = World(minimum=1)
    item = world.add(1, source="s", channel="c")
    world.triage.rate(item.id, Rating.UP)
    back = Undo(item.id, State.NEW, None, False, Rating.DOWN, NOW)
    assert world.triage.restore(back).rating is Rating.DOWN
    world.triage.restore_many((Undo(item.id, State.DONE, None, True),))
    stored = world.stored(item)
    assert (stored.state, stored.starred, stored.rating, stored.rated_at) == (
        State.DONE,
        True,
        Rating.NONE,
        None,
    )


def test_stars_and_opens_still_teach_and_snoozing_still_does_not() -> None:
    world = World(minimum=1)
    item = world.add(1, source="s", channel="c")
    world.triage.act(item.id, Action.OPEN)
    world.triage.act(item.id, Action.STAR)
    world.triage.act(item.id, Action.SNOOZE, until=NOW + timedelta(days=1))
    assert [s.kind for s in world.signals.all()] == [SignalKind.OPEN, SignalKind.STAR, SignalKind.SNOOZE]


# --- the API and the command line ---


@pytest.fixture
def api(tmp_path: Path) -> Any:
    instance = Api(Lookout(tmp_path))
    instance.services.items.save(make_item("https://x/a", title="Alpha"))
    yield instance
    instance.services.close()


def rate(api: Any, item_id: str, rating: int) -> Any:
    return api.client.post(f"/api/items/{item_id}/rating", json={"rating": rating})


def test_the_api_rates_an_item_and_says_how_to_undo_it(api: Any) -> None:
    [item] = api.items()
    assert item["rating"] == 0
    answer = rate(api, item["id"], 1).json()
    assert (answer["item"]["rating"], answer["undo"]["rating"]) == (1, 0)
    assert api.items()[0]["rating"] == 1
    assert rate(api, item["id"], 1).json()["item"]["rating"] == 0  # the same thumb again clears it
    assert rate(api, item["id"], -1).json()["item"]["rating"] == -1
    assert len(api.items()) == 1  # a rating never removes the item


def test_the_api_puts_a_rating_back_with_the_rest(api: Any) -> None:
    [item] = api.items()
    undo = rate(api, item["id"], -1).json()["undo"]
    rate(api, item["id"], -1)
    restored = api.client.post(
        f"/api/items/{item['id']}/restore", json={**undo, "rating": -1, "rated_at": None}
    )
    assert restored.json()["rating"] == -1
    many = api.client.post("/api/items/restore-many", json={"entries": [{"id": item["id"], **undo}]})
    assert many.json()["changed"] == 1
    assert api.items()[0]["rating"] == 0


@pytest.mark.parametrize(("item_id", "rating", "status"), [("nope", 1, 404), ("x", 2, 422), ("x", -2, 422)])
def test_a_bad_rating_or_item_is_refused(api: Any, item_id: str, rating: int, status: int) -> None:
    assert rate(api, item_id, rating).status_code == status


def test_the_command_line_rates_and_clears(tmp_path: Path) -> None:
    lookout = Lookout(tmp_path)
    lookout.network.chat = lambda _request: "{}"
    lookout("run")
    item = lookout("inbox").splitlines()[0].split()[2]
    assert "[new]" in lookout("rate", item, "up") or "[seen]" in lookout("rate", item, "down")
    assert lookout("rate", item, "none")
    assert lookout("rate", item, "up")
    assert "no item nope" in lookout("rate", "nope", "up", exit_code=1)


# --- the migration ---

LEGACY = {"a": "dismissed", "b": "done", "c": "new", "d": "dismissed", "e": "new"}


def legacy_database(path: Path) -> None:
    """A database as it was before thumbs: dismissed and done items, and done and dismiss signals."""
    with sqlite3.connect(path) as db:
        for step in (
            store.migrate_v1,
            store.migrate_v2,
            store.migrate_v3,
            store.migrate_v4,
            store.migrate_v5,
        ):
            step(db)
        db.execute("PRAGMA user_version = 5")
        for key, state in LEGACY.items():
            item = make_item(f"https://old.test/{key}", title=key)
            raw: dict[str, Any] = json.loads(encode(item))
            raw.pop("rating")
            raw.pop("rated_at")
            raw["state"] = state
            db.execute(
                "INSERT INTO items (id, priority, state, starred, channel, author, sources, search, rank,"
                " pending, published_at, snoozed_until, data)"
                " VALUES (?, 2, ?, 0, 'Other', '', '|blog|', ?, 0, 1, ?, NULL, ?)",
                (item.id, state, key, NOW.isoformat(), json.dumps(raw)),
            )
        ids = {k: make_item(f"https://old.test/{k}").id for k in LEGACY}
        for item_id, kind, at in (
            (ids["a"], "dismiss", "2026-10-01T10:00:00+00:00"),
            (ids["b"], "done", "2026-10-02T10:00:00+00:00"),
            (ids["c"], "done", "2026-10-03T10:00:00+00:00"),
            (ids["c"], "dismiss", "2026-10-04T10:00:00+00:00"),
            (ids["e"], "open", "2026-10-05T10:00:00+00:00"),
            (ids["e"], "star", "2026-10-06T10:00:00+00:00"),
        ):
            db.execute("INSERT INTO signals (item_id, kind, at) VALUES (?, ?, ?)", (item_id, kind, at))


def test_opening_an_older_database_turns_dismissed_into_done_and_old_signals_into_ratings(
    tmp_path: Path,
) -> None:
    path = tmp_path / "lookout.db"
    legacy_database(path)
    db = database(path)
    items = {i.title: i for i in SqliteItemRepository(db).all()}
    assert {k: items[k].state for k in LEGACY} == {
        "a": State.DONE,
        "b": State.DONE,
        "c": State.NEW,
        "d": State.DONE,
        "e": State.NEW,
    }
    assert {k: items[k].rating for k in LEGACY} == {
        "a": Rating.DOWN,
        "b": Rating.UP,
        "c": Rating.DOWN,  # the latest of its signals wins
        "d": Rating.NONE,  # cleared in bulk: no signal, no rating
        "e": Rating.NONE,
    }
    assert items["a"].rated_at is not None
    assert items["b"].rated_at is not None
    assert items["d"].rated_at is None
    assert [s.kind for s in SqliteSignalRepository(db).all()] == [SignalKind.OPEN, SignalKind.STAR]
    assert (tmp_path / "lookout.db.bak-v5").exists()
    states = {r["state"] for r in db.query("SELECT state FROM items")}
    assert states == {"done", "new"}
