"""Scenarios of openspec/specs/retention and the ordering and age filters of triage (ADR 0016)."""

import sqlite3
from datetime import timedelta
from pathlib import Path
from typing import Any, cast

import pytest
from tests.cli_support import FEED_URL, Lookout, reading
from tests.support import NOW, FixedClock, make_item, repository
from tests.test_http import Api

from lookout.application.errors import ConfigError
from lookout.application.expire import AgeLimited, Expire
from lookout.application.ports import InboxQuery, Order
from lookout.bootstrap.container import build, load
from lookout.domain.advisory import Advisory
from lookout.domain.policy import PriorityPolicy
from lookout.domain.priority import Priority
from lookout.domain.raw import RawItem
from lookout.domain.retention import Retention
from lookout.domain.severity import Severity
from lookout.domain.state import State


def ago(**delta: float) -> Any:
    return NOW - timedelta(**delta)


# --- freshness at the door ---


class Fixed:
    name = "feed"

    def __init__(self, *raws: RawItem) -> None:
        self.raws = raws

    def fetch(self) -> tuple[RawItem, ...]:
        return self.raws


def raw(url: str, published_at: Any) -> RawItem:
    return RawItem("feed", url, url, "", published_at)


def test_entries_older_than_the_limit_are_left_out_and_undated_ones_stay() -> None:
    inner = Fixed(
        raw("https://x/new", ago(days=2)), raw("https://x/old", ago(days=45)), raw("https://x/none", None)
    )
    kept = AgeLimited(inner, 30, FixedClock()).fetch()
    assert [r.url for r in kept] == ["https://x/new", "https://x/none"]
    assert AgeLimited(inner, 30, FixedClock()).name == "feed"


def test_a_limit_of_zero_keeps_everything() -> None:
    inner = Fixed(raw("https://x/old", ago(days=900)))
    assert len(AgeLimited(inner, 0, FixedClock()).fetch()) == 1


def test_a_longer_limit_on_a_source_brings_older_entries_in_at_the_next_run(tmp_path: Path) -> None:
    api = Api(Lookout(tmp_path))
    try:
        api.lookout.clock.advance(days=40)  # the feed's dated entry is now 41 days old
        api.run()
        before = api.services.items.search(InboxQuery(limit=100)).total
        body: dict[str, Any] = {
            "type": "rss",
            "settings": {"url": FEED_URL, "max_age_days": 0},
            "channels": cast("list[str]", []),
            "keywords": cast("list[str]", []),
        }
        assert api.client.put("/api/sources/blog", json=body).status_code == 200
        api.run()
        # Brought in, then expired at once: older than its priority's limit, it waits in the expired view.
        assert api.services.items.search(InboxQuery(limit=100)).total == before + 1
        assert len(api.items()) == before
    finally:
        api.services.close()


@pytest.mark.parametrize("days", [-1, True, "many", 1.5])
def test_max_age_days_is_validated_for_every_type(tmp_path: Path, days: object) -> None:
    lookout = Lookout(
        tmp_path, sources=[{"name": "blog", "type": "rss", "url": FEED_URL, "max_age_days": days}]
    )
    lookout.write()
    with pytest.raises(ConfigError, match="'max_age_days' must be a whole number of days"):
        build(load(lookout.path, {}))


# --- the rules and age ---

ADVISORY = Advisory(Severity.CRITICAL, "django", "pypi", watched=True)


@pytest.mark.parametrize(
    ("age", "floor"),
    [(None, Priority.P0), (timedelta(days=3), Priority.P0), (timedelta(days=200), Priority.P3)],
)
def test_a_rule_floor_only_binds_recent_items(age: timedelta | None, floor: Priority) -> None:
    decision = PriorityPolicy().decide(advisory=ADVISORY, stack_matches=(), enrichment=None, age=age)
    assert decision.priority is floor


def test_the_window_can_be_switched_off() -> None:
    policy = PriorityPolicy(rules_window_days=0)
    assert (
        policy.decide(advisory=ADVISORY, stack_matches=(), enrichment=None, age=timedelta(days=900)).priority
        is Priority.P0
    )


# --- expiry ---


def world(retention: Retention | None = None) -> tuple[Any, Expire, FixedClock]:
    repo = repository()
    clock = FixedClock()
    return repo, Expire(repo, clock, retention or Retention()), clock


def test_untouched_items_expire_by_how_urgent_they_were() -> None:
    repo, expire, _ = world()
    kept: dict[str, Any] = {}
    for priority, age in ((Priority.P3, 8), (Priority.P2, 15), (Priority.P1, 31), (Priority.P0, 400)):
        item = make_item(f"https://x/{priority.name}", priority=priority, published_at=ago(days=age))
        repo.save(item)
        kept[priority.name] = item
    young = make_item("https://x/young", priority=Priority.P3, published_at=ago(days=6))
    repo.save(young)
    assert expire.run() == 3
    states = {name: repo.get(item.id).state for name, item in kept.items()}
    assert states == {"P3": State.EXPIRED, "P2": State.EXPIRED, "P1": State.EXPIRED, "P0": State.NEW}
    assert repo.get(young.id).state is State.NEW
    assert expire.run() == 0


def test_expiry_never_touches_what_the_user_decided_or_starred() -> None:
    repo, expire, _ = world()
    old = ago(days=100)
    items = {
        "done": make_item("https://x/done", priority=Priority.P3, published_at=old).mark_done(),
        "snoozed": make_item("https://x/snz", priority=Priority.P3, published_at=old).snooze(
            NOW + timedelta(days=1)
        ),
        "starred": make_item("https://x/star", priority=Priority.P3, published_at=old).star(),
        "seen": make_item("https://x/seen", priority=Priority.P3, published_at=old).open(),
    }
    for item in items.values():
        repo.save(item)
    assert expire.run() == 1
    assert {k: repo.get(v.id).state for k, v in items.items()} == {
        "done": State.DONE,
        "snoozed": State.SNOOZED,
        "starred": State.NEW,
        "seen": State.EXPIRED,
    }


def test_an_expired_item_can_be_reopened_and_the_limits_can_be_set() -> None:
    repo, expire, clock = world(
        Retention(expire_after_days={Priority.P0: 3, Priority.P1: None, Priority.P2: None, Priority.P3: None})
    )
    item = make_item("https://x/p0", priority=Priority.P0, published_at=ago(days=4))
    repo.save(item)
    assert expire.run() == 1
    assert repo.get(item.id).reopen().state is State.SEEN
    clock.advance(days=0)


def test_has_expired_tells_the_same_story_for_one_item() -> None:
    retention = Retention()
    assert retention.has_expired(State.NEW, Priority.P3, ago(days=8), NOW, starred=False)
    assert not retention.has_expired(State.DONE, Priority.P3, ago(days=8), NOW, starred=False)
    assert not retention.has_expired(State.NEW, Priority.P0, ago(days=800), NOW, starred=False)


# --- orders and age filters ---


def test_the_latest_order_is_strictly_newest_first_and_triage_is_by_priority() -> None:
    repo = repository()
    old_urgent = make_item("https://x/a", priority=Priority.P0, published_at=ago(days=5))
    new_quiet = make_item("https://x/b", priority=Priority.P3, published_at=ago(hours=1))
    mid = make_item("https://x/c", priority=Priority.P1, published_at=ago(days=1))
    for item in (old_urgent, new_quiet, mid):
        repo.save(item)
    triage = [i.id for i in repo.search(InboxQuery()).items]
    latest = [i.id for i in repo.search(InboxQuery(order=Order.DATE)).items]
    assert triage == [old_urgent.id, mid.id, new_quiet.id]
    assert latest == [new_quiet.id, mid.id, old_urgent.id]


def test_items_can_be_filtered_by_age_and_paged_with_the_real_total() -> None:
    repo = repository()
    for n in range(7):
        repo.save(make_item(f"https://x/{n}", published_at=ago(days=n * 3)))
    older = repo.search(InboxQuery(published_before=ago(days=10)))
    assert older.total == 3
    newer = repo.search(InboxQuery(published_after=ago(days=10), order=Order.DATE, limit=2, offset=2))
    assert (newer.total, len(newer.items)) == (4, 2)


# --- configuration and the whole application ---


def test_retention_is_read_from_the_file(tmp_path: Path) -> None:
    path = tmp_path / "lookout.yaml"
    path.write_text(
        "retention:\n  max_age_days: 10\n  rules_window_days: 5\n  expire_after_days: {p0: 60, p3: 0}\n"
    )
    retention = load(path, {}).retention
    assert (retention.max_age_days, retention.rules_window_days) == (10, 5)
    assert retention.expiry(Priority.P0) == timedelta(days=60)
    assert retention.expiry(Priority.P3) is None
    assert retention.expiry(Priority.P2) == timedelta(days=14)


@pytest.mark.parametrize(
    ("text", "message"),
    [
        ("retention: {max_age_days: -1}", "'max_age_days' must be a whole number"),
        ("retention: {expire_after_days: {p9: 3}}", "has no level 'p9'"),
        ("retention: {expire_after_days: {p1: x}}", "'p1' must be a whole number"),
    ],
)
def test_bad_retention_is_refused(tmp_path: Path, text: str, message: str) -> None:
    path = tmp_path / "lookout.yaml"
    path.write_text(text)
    with pytest.raises(ConfigError, match=message):
        load(path, {})


def test_opening_the_application_expires_what_is_due_and_a_run_does_too(tmp_path: Path) -> None:
    first = Api(Lookout(tmp_path))
    old = make_item("https://x/old", priority=Priority.P3, published_at=ago(days=20))
    first.services.items.save(old)
    first.services.close()
    again = Api(Lookout(tmp_path))
    try:
        assert again.services.items.get(old.id).state is State.EXPIRED  # type: ignore[union-attr]
        again.services.items.save(
            make_item("https://x/old2", priority=Priority.P3, published_at=ago(days=45))
        )
        again.lookout.network.chat = lambda _request: reading()
        again.run()
        assert again.services.items.get(make_item("https://x/old2").id).state is State.EXPIRED  # type: ignore[union-attr]
    finally:
        again.services.close()


# --- the API: orders, age, the expired view and sweeps ---


@pytest.fixture
def api(tmp_path: Path) -> Any:
    instance = Api(Lookout(tmp_path, channels=[{"name": "AI"}]))
    repo = instance.services.items
    for n, (priority, age, channel) in enumerate(
        [(Priority.P0, 20, "AI"), (Priority.P2, 2, "AI"), (Priority.P3, 1, "Other"), (Priority.P1, 15, "AI")]
    ):
        repo.save(
            make_item(
                f"https://x/{n}",
                title=f"item {n}",
                priority=priority,
                channel=channel,
                published_at=ago(days=age),
            )
        )
    yield instance
    instance.services.close()


def titles(items: list[dict[str, Any]]) -> list[str]:
    return [i["title"] for i in items]


def test_the_list_can_be_ordered_by_priority_or_by_date(api: Any) -> None:
    assert titles(api.items()) == ["item 0", "item 3", "item 1", "item 2"]
    assert titles(api.items(order="date")) == ["item 2", "item 1", "item 3", "item 0"]


def test_the_list_can_be_filtered_by_age_and_paged(api: Any) -> None:
    assert titles(api.items(older_than_days=10, order="date")) == ["item 3", "item 0"]
    assert titles(api.items(newer_than_days=10, order="date")) == ["item 2", "item 1"]
    page = api.client.get("/api/items", params={"order": "date", "limit": 1, "offset": 1}).json()
    assert (page["total"], titles(page["items"])) == (4, ["item 1"])


def test_expired_items_are_in_their_own_view_and_reopening_brings_them_back(api: Any) -> None:
    victim = api.items()[3]
    api.services.items.save(api.services.items.get(victim["id"]).expire())  # type: ignore[union-attr]
    assert "item 2" not in titles(api.items())
    assert titles(api.items(state="expired")) == ["item 2"]
    assert api.act(victim["id"], "reopen").json()["item"]["state"] == "seen"
    assert "item 2" in titles(api.items())


def sweep(api: Any, **body: Any) -> Any:
    return api.client.post("/api/items/sweep", json=body)


def test_a_dry_run_counts_and_samples_and_changes_nothing(api: Any) -> None:
    answer = sweep(api, action="done", dry_run=True, filter={"channel": ["AI"], "older_than_days": 10}).json()
    assert (answer["matched"], answer["changed"], answer["undo"]) == (2, 0, [])
    assert sorted(titles(answer["sample"])) == ["item 0", "item 3"]
    assert len(api.items()) == 4


def test_a_sweep_acts_on_exactly_what_the_filter_matches_and_can_be_undone(api: Any) -> None:
    answer = sweep(api, action="done", filter={"channel": ["AI"], "older_than_days": 10}).json()
    assert (answer["matched"], answer["changed"]) == (2, 2)
    assert titles(api.items(order="date")) == ["item 2", "item 1"]
    undone = api.client.post("/api/items/restore-many", json={"entries": answer["undo"]})
    assert (undone.status_code, undone.json()["changed"]) == (200, 2)
    assert len(api.items()) == 4


def test_a_sweep_teaches_the_profile_nothing(api: Any) -> None:
    sweep(api, action="done", filter={})
    raw = sqlite3.connect(api.lookout.config["database"])
    try:
        assert raw.execute("SELECT count(*) FROM signals").fetchone() == (0,)
    finally:
        raw.close()


def test_a_sweep_can_snooze_and_refuses_what_makes_no_sense_or_is_too_big(
    api: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    assert sweep(api, action="snooze", hours=2, filter={"channel": ["Other"]}).json()["changed"] == 1
    assert sweep(api, action="reopen", filter={}).status_code == 409
    monkeypatch.setattr("lookout.application.triage.MAX_SWEEP", 1)
    refused = sweep(api, action="done", filter={})
    assert (refused.status_code, "narrow the filter" in refused.json()["detail"]) == (422, True)
    assert (
        api.client.post(
            "/api/items/restore-many",
            json={"entries": [{"id": "nope", "state": "new", "snoozed_until": None, "starred": False}]},
        ).status_code
        == 404
    )


# --- the counts beside the list tell the truth about the list ---


def test_the_tree_counts_what_the_list_would_show_for_the_same_filters(api: Any) -> None:
    """Counts used to include done and expired items, so 2441 beside a list of 112."""
    repo = api.services.items
    finished = make_item("https://x/finished", channel="AI", published_at=ago(days=1)).mark_done()
    gone = make_item("https://x/gone", channel="AI", published_at=ago(days=40)).expire()
    repo.save(finished)
    repo.save(gone)

    def counts(**params: Any) -> dict[str, int]:
        found = api.client.get("/api/taxonomy", params=params).json()["channels"]
        return {c["name"]: c["items"] for c in found}

    assert counts()["AI"] == len(api.items(channel="AI")) == 3  # not 5: done and expired are not in the inbox
    assert counts(state="expired")["AI"] == 1
    assert counts(older_than_days=10)["AI"] == 2
    assert counts(newer_than_days=10, priority="P2")["AI"] == 1
    assert counts(text="item 3")["AI"] == 1
    assert counts(source="nobody")["AI"] == 0
    assert counts(starred=True)["AI"] == 0
    for params in ({}, {"state": "expired"}, {"older_than_days": 10}, {"priority": "P0"}):
        shown = api.client.get("/api/items", params={"channel": "AI", "limit": 100, **params}).json()["total"]
        assert counts(**params)["AI"] == shown, params
