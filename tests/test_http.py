"""The HTTP API end to end on the real wiring (openspec: dashboard, triage, scheduling)."""

import time
from collections.abc import Callable, Iterator
from dataclasses import replace
from pathlib import Path
from typing import TYPE_CHECKING, Any

import pytest
from tests.cli_support import Lookout, http_client, reading

if TYPE_CHECKING:
    from lookout.application.services import Services

from lookout.adapters.http.app import create_app
from lookout.application.runs import RunCoordinator


class Api:
    """A running instance with a client; ``run`` fills the inbox through the real pipeline."""

    def __init__(self, lookout: Lookout, dashboard: Path | None = None) -> None:
        self.lookout = lookout
        self.services: Services = lookout.services()
        self.services = replace(
            self.services, runs=RunCoordinator(self.services.run, lookout.clock, spawn=lambda work: work())
        )
        self.client = http_client(create_app(self.services, dashboard))

    def run(self) -> None:
        assert self.client.post("/api/run").status_code == 202

    def items(self, **params: Any) -> list[dict[str, Any]]:
        response = self.client.get("/api/items", params=params)
        assert response.status_code == 200
        return response.json()["items"]

    def act(self, item_id: str, action: str, **body: Any) -> Any:
        return self.client.post(f"/api/items/{item_id}/actions", json={"action": action, **body})


@pytest.fixture
def api(tmp_path: Path) -> Iterator[Api]:
    lookout = Lookout(tmp_path)
    instance = Api(lookout)
    yield instance
    instance.services.close()


@pytest.fixture
def filled(api: Api) -> Api:
    api.lookout.network.chat = lambda request: reading(
        score=95 if "Django" in request.content.decode() else 10,
        kind="security" if "Django" in request.content.decode() else "other",
    )
    api.run()
    return api


def test_health(api: Api) -> None:
    assert api.client.get("/api/health").json()["status"] == "ok"


def test_run_fills_the_inbox_with_prioritised_items(filled: Api) -> None:
    items = filled.items()
    assert [i["priority"] for i in items] == ["P0", "P3", "P3"]
    top = items[0]
    assert (top["title"], top["kind"], top["score"], top["unread"]) == (
        "Django 6.0 released",
        "security",
        95,
        False,
    )
    assert top["stack_matches"] == ["django"]
    assert top["summary"] == "A summary."
    assert top["priority_label"] == "act today"
    assert filled.client.get("/api/items", params={"limit": 2, "offset": 2}).json()["total"] == 3


def test_filters(filled: Api) -> None:
    assert len(filled.items(priority="P0")) == 1
    assert len(filled.items(priority=["P0", "P3"])) == 3
    assert len(filled.items(kind="security")) == 1
    assert len(filled.items(source="blog")) == 3
    assert len(filled.items(source="nope")) == 0
    assert len(filled.items(text="django")) == 1
    assert len(filled.items(starred="true")) == 0
    assert len(filled.items(state="done")) == 0
    assert filled.client.get("/api/items", params={"priority": "P9"}).status_code == 422
    assert filled.client.get("/api/items", params={"limit": 0}).status_code == 422


def test_item_detail_has_the_body_and_the_rank_explanation(filled: Api) -> None:
    item_id = filled.items()[0]["id"]
    detail = filled.client.get(f"/api/items/{item_id}").json()
    assert detail["body"] == "Django 6.0 is out."
    assert detail["explanation"]["model_score"] == 95
    assert detail["explanation"]["priority"] == "P0"
    assert filled.client.get("/api/items/nope").status_code == 404


def test_actions_and_undo(filled: Api) -> None:
    item_id = filled.items()[0]["id"]
    opened = filled.act(item_id, "open").json()
    assert opened["item"]["state"] == "seen"
    done = filled.act(item_id, "done").json()
    assert done["item"]["state"] == "done"
    assert len(filled.items()) == 2
    restored = filled.client.post(f"/api/items/{item_id}/restore", json=done["undo"])
    assert restored.json()["state"] == "seen"
    assert len(filled.items()) == 3
    assert filled.act(item_id, "star").json()["item"]["starred"] is True
    assert len(filled.items(starred="true")) == 1


def test_snooze_by_hours_and_by_date_with_or_without_a_zone(filled: Api) -> None:
    first, second, third = (i["id"] for i in filled.items())
    hours = filled.act(first, "snooze", hours=2).json()["item"]
    assert hours["state"] == "snoozed"
    assert hours["snoozed_until"].startswith("2026-10-24T11:00:00")
    assert filled.act(second, "snooze", until="2026-10-25T09:00:00+00:00").json()["item"]["snoozed_until"]
    assert filled.act(third, "snooze", until="2026-10-26T09:00:00").json()["item"]["snoozed_until"]
    assert filled.items() == []
    filled.lookout.clock.advance(days=3)
    assert len(filled.items()) == 3


def test_refusals(filled: Api) -> None:
    item_id = filled.items()[0]["id"]
    assert filled.act("nope", "done").status_code == 404
    assert filled.act(item_id, "reopen").status_code == 409
    assert filled.act(item_id, "explode").status_code == 422
    assert filled.act(item_id, "snooze", hours=0).status_code == 422
    assert (
        filled.client.post(
            "/api/items/nope/restore", json={"state": "new", "snoozed_until": None, "starred": False}
        ).status_code
        == 404
    )


def test_bulk_actions(filled: Api) -> None:
    ids = [i["id"] for i in filled.items()]
    assert filled.client.post("/api/items/bulk", json={"ids": ids[:2], "action": "done"}).json() == {
        "changed": 2
    }
    assert len(filled.items()) == 1
    assert (
        filled.client.post("/api/items/bulk", json={"ids": [ids[2], "nope"], "action": "dismiss"}).status_code
        == 404
    )
    assert (
        filled.client.post("/api/items/bulk", json={"ids": [ids[2]], "action": "reopen"}).status_code == 409
    )
    snoozed = filled.client.post("/api/items/bulk", json={"ids": [ids[2]], "action": "snooze", "hours": 1})
    assert snoozed.json() == {"changed": 1}
    assert filled.client.post("/api/items/bulk", json={"ids": [], "action": "done"}).status_code == 422


def test_mark_everything_below_a_priority_as_seen(filled: Api) -> None:
    assert filled.client.post("/api/items/seen-below", json={"priority": "P1"}).json() == {"changed": 2}
    assert [i["state"] for i in filled.items()] == ["new", "seen", "seen"]
    assert filled.client.post("/api/items/seen-below", json={"priority": "P7"}).status_code == 422


def test_sources_can_be_switched_off_and_on(filled: Api) -> None:
    (blog,) = filled.client.get("/api/sources").json()
    assert (blog["name"], blog["type"], blog["enabled"], blog["items_seen"]) == ("blog", "rss", True, 3)
    off = filled.client.patch("/api/sources/blog", json={"enabled": False}).json()
    assert off["enabled"] is False
    filled.lookout.network.feed = (filled.lookout.network.feed or b"").replace(b"nodate", b"another")  # type: ignore[union-attr]
    filled.run()
    assert filled.client.get("/api/run").json()["sources"][0]["skipped"] is True
    assert filled.client.patch("/api/sources/blog", json={"enabled": True}).json()["enabled"] is True
    assert filled.client.patch("/api/sources/nope", json={"enabled": True}).status_code == 404


def test_a_source_disabled_in_the_file_cannot_be_enabled_from_the_dashboard(tmp_path: Path) -> None:
    lookout = Lookout(
        tmp_path, sources=[{"name": "off", "type": "rss", "url": "https://x", "enabled": False}]
    )
    instance = Api(lookout)
    try:
        assert instance.client.get("/api/sources").json()[0]["enabled"] is False
        assert instance.client.patch("/api/sources/off", json={"enabled": True}).status_code == 409
        assert instance.client.patch("/api/sources/off", json={"enabled": False}).json()["enabled"] is False
    finally:
        instance.services.close()


def test_run_status_reports_the_last_run(filled: Api) -> None:
    status = filled.client.get("/api/run").json()
    assert (status["running"], status["enriched"], status["failed"], status["waiting"]) == (False, 3, 0, 0)
    assert status["sources"][0] == {"name": "blog", "fetched": 3, "new": 3, "error": None, "skipped": False}
    assert status["finished_at"] is not None


def test_run_endpoint_never_overlaps_runs(api: Api) -> None:
    pending: list[Callable[[], None]] = []
    coordinator = RunCoordinator(api.services.run, api.lookout.clock, spawn=pending.append)
    client = http_client(create_app(replace(api.services, runs=coordinator)))
    first = client.post("/api/run").json()
    second = client.post("/api/run").json()
    assert (first["started"], first["running"], second["started"], second["running"]) == (
        True,
        True,
        False,
        True,
    )
    assert len(pending) == 1
    pending[0]()
    assert client.get("/api/run").json()["running"] is False


def test_a_crashing_run_is_reported_not_raised(api: Api) -> None:
    def boom() -> Any:
        msg = "disk full"
        raise OSError(msg)

    coordinator = RunCoordinator(boom, api.lookout.clock, spawn=lambda work: work())
    client = http_client(create_app(replace(api.services, runs=coordinator)))
    client.post("/api/run")
    status = client.get("/api/run").json()
    assert (status["running"], status["error"]) == (False, "OSError: disk full")


def test_a_real_background_thread_finishes_the_run(api: Api) -> None:
    real = http_client(
        create_app(replace(api.services, runs=RunCoordinator(api.services.run, api.lookout.clock)))
    )
    assert real.post("/api/run").status_code == 202
    for _ in range(200):
        if not real.get("/api/run").json()["running"]:
            break
        time.sleep(0.01)
    assert real.get("/api/run").json()["finished_at"] is not None


def test_forgetting_the_profile(filled: Api) -> None:
    assert filled.client.delete("/api/profile").status_code == 204


def test_the_dashboard_is_served_with_a_single_page_fallback(tmp_path: Path) -> None:
    dist = tmp_path / "dist"
    (dist / "assets").mkdir(parents=True)
    (dist / "index.html").write_text("<html>app</html>")
    (dist / "assets" / "app.js").write_text("console.log(1)")
    (dist / "favicon.svg").write_text("<svg/>")
    (tmp_path / "secret.txt").write_text("nope")
    instance = Api(Lookout(tmp_path / "x" if (tmp_path / "x").mkdir() is None else tmp_path), dist)
    try:
        client = instance.client
        assert client.get("/").text == "<html>app</html>"
        assert client.get("/inbox/anything").text == "<html>app</html>"
        assert client.get("/assets/app.js").text == "console.log(1)"
        assert client.get("/favicon.svg").text == "<svg/>"
        assert client.get("/../secret.txt").text == "<html>app</html>"
        assert client.get("/api/nothing").status_code == 404
    finally:
        instance.services.close()


def test_without_a_built_dashboard_only_the_api_answers(tmp_path: Path) -> None:
    instance = Api(Lookout(tmp_path), tmp_path / "missing")
    try:
        assert instance.client.get("/").status_code == 404
        assert instance.client.get("/api/health").status_code == 200
    finally:
        instance.services.close()


def test_dashboard_without_an_assets_folder(tmp_path: Path) -> None:
    dist = tmp_path / "dist"
    dist.mkdir()
    (dist / "index.html").write_text("<html>bare</html>")
    instance = Api(Lookout(tmp_path), dist)
    try:
        assert instance.client.get("/").text == "<html>bare</html>"
    finally:
        instance.services.close()


CHANNELS = [
    {"name": "AI", "description": "Models and tools"},
    {"name": "Rust"},
    {"name": "Security"},
    {"name": "Web"},
]


@pytest.fixture
def sorted_api(tmp_path: Path) -> Iterator[Api]:
    """The demo inbox, filed in declared channels."""
    instance = Api(Lookout(tmp_path, channels=CHANNELS))
    assert instance.services.seed_demo() == 6
    yield instance
    instance.services.close()


def test_the_taxonomy_lists_the_channels_with_other_and_the_kinds(sorted_api: Api) -> None:
    taxonomy = sorted_api.client.get("/api/taxonomy").json()
    assert [c["name"] for c in taxonomy["channels"]] == ["AI", "Rust", "Security", "Web", "Other"]
    assert taxonomy["channels"][0]["description"] == "Models and tools"
    assert "security" in taxonomy["kinds"]
    assert "schedule" in taxonomy["kinds"]


def test_items_carry_their_channel_kind_author_and_the_articles_tags(sorted_api: Api) -> None:
    django = next(i for i in sorted_api.items() if i["title"].startswith("Django"))
    assert (django["channel"], django["kind"], django["author"]) == (
        "Security",
        "security",
        "Django Security Team",
    )
    assert django["feed_tags"] == ["django"]
    assert django["tags"] == ["django", "sql-injection"]


def test_the_inbox_filters_by_channel_and_by_kind_independently(sorted_api: Api) -> None:
    assert {i["channel"] for i in sorted_api.items()} == {"Security", "Web", "Other", "Rust", "AI"}
    assert [i["title"][:6] for i in sorted_api.items(channel="Rust")] == ["Show H"]
    assert len(sorted_api.items(channel=["Security", "AI"])) == 3
    assert len(sorted_api.items(kind="security")) == 2
    assert len(sorted_api.items(kind="release")) == 2
    assert [i["channel"] for i in sorted_api.items(kind="release", channel="Web")] == ["Web"]
    assert sorted_api.items(kind="release", channel="Rust") == []


def test_the_text_filter_also_searches_the_author(sorted_api: Api) -> None:
    assert [i["author"] for i in sorted_api.items(text="ferris")] == ["ferris"]


def test_demo_items_fall_back_to_other_when_their_channel_is_not_declared(api: Api) -> None:
    api.services.seed_demo()
    assert {i["channel"] for i in api.items()} == {"Other"}
