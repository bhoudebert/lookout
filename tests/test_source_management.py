"""Scenarios of openspec/specs/source-management (ADR 0013)."""

import sqlite3
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
from tests.cli_support import FEED_URL, Lookout
from tests.support import database
from tests.test_http import Api

from lookout.adapters.store import sqlite as store
from lookout.adapters.store.sqlite import (
    SqliteChannelDefinitions,
    SqliteFlags,
    SqliteItemRepository,
    SqliteSourceDefinitions,
    SqliteSourceStatusRepository,
)
from lookout.application.errors import ConfigError
from lookout.application.ports_sources import SourceStatus
from lookout.application.registry import Registry
from lookout.domain.channel import OTHER, Channel
from lookout.domain.source import SourceDef

RUST_BLOG = {"name": "rust-blog", "type": "rss", "settings": {"url": FEED_URL}, "channels": ["Rust"]}


@pytest.fixture
def api(tmp_path: Path) -> Iterator[Api]:
    """An instance with two channels and no source: everything is added from the dashboard."""
    instance = Api(
        Lookout(tmp_path, sources=[], channels=[{"name": "Rust"}, {"name": "AI", "description": "Models"}])
    )
    yield instance
    instance.services.close()


def post(api: Api, path: str, body: dict[str, Any]) -> Any:
    return api.client.post(path, json=body)


def sources(api: Api) -> list[dict[str, Any]]:
    return api.client.get("/api/sources").json()


# --- what a form needs ---


def test_the_api_publishes_the_types_and_their_fields(api: Api) -> None:
    types = {t["name"]: t for t in api.client.get("/api/source-types").json()}
    assert set(types) == {"rss", "github", "osv"}
    assert [(f["name"], f["kind"], f["required"]) for f in types["rss"]["fields"]] == [("url", "text", True)]
    github = {f["name"]: f for f in types["github"]["fields"]}
    assert (github["repos"]["kind"], github["repos"]["required"]) == ("list", True)
    assert github["watch"]["default"] == ["releases", "advisories"]
    osv = {f["name"]: f for f in types["osv"]["fields"]}
    assert (osv["kev"]["kind"], osv["kev"]["default"], osv["since_days"]["kind"]) == ("bool", True, "number")


# --- adding a source ---


def test_a_new_source_is_fetched_by_the_next_run_without_a_restart(api: Api) -> None:
    created = post(api, "/api/sources", RUST_BLOG)
    assert created.status_code == 201
    assert (created.json()["name"], created.json()["channels"], created.json()["enabled"]) == (
        "rust-blog",
        ["Rust"],
        True,
    )
    api.run()
    assert {i["channel"] for i in api.items()} == {"Rust"}
    assert sources(api)[0]["items_seen"] == 3


def test_a_name_is_unique_ignoring_case_and_is_trimmed(api: Api) -> None:
    assert post(api, "/api/sources", RUST_BLOG).status_code == 201
    again = post(api, "/api/sources", {**RUST_BLOG, "name": "  RUST-BLOG "})
    assert (again.status_code, "already exists" in again.json()["detail"]) == (409, True)
    spaced = post(api, "/api/sources", {**RUST_BLOG, "name": "  other "})
    assert spaced.json()["name"] == "other"


@pytest.mark.parametrize(
    ("body", "message"),
    [
        ({**RUST_BLOG, "name": "  "}, "needs a name"),
        ({**RUST_BLOG, "type": "ftp"}, "supported types: rss, github, osv"),
        ({**RUST_BLOG, "settings": {}}, "needs a 'url'"),
        ({**RUST_BLOG, "settings": {"url": "ftp://x"}}, "'url' must start with http"),
        ({**RUST_BLOG, "channels": ["Gardening"]}, "feeds the channel 'Gardening', which does not exist"),
        (
            {"name": "g", "type": "github", "settings": {"repos": ["nope"]}},
            "'nope' is not of the form owner/name",
        ),
        (
            {"name": "g", "type": "github", "settings": {"repos": ["o/r"], "watch": ["stars"]}},
            "'watch' must be a list",
        ),
        ({"name": "o", "type": "osv", "settings": {"kev": "yes"}}, "'kev' must be true or false"),
    ],
)
def test_invalid_sources_are_refused_with_the_reason_and_nothing_is_stored(
    api: Api, body: dict[str, Any], message: str
) -> None:
    refused = post(api, "/api/sources", body)
    assert refused.status_code == 422
    assert message in refused.json()["detail"]
    assert sources(api) == []


def test_channels_are_matched_ignoring_case_and_stored_as_declared(api: Api) -> None:
    created = post(api, "/api/sources", {**RUST_BLOG, "channels": ["rust", "RUST", "ai"]})
    assert created.json()["channels"] == ["Rust", "AI"]


def test_keywords_are_trimmed_and_blanks_dropped(api: Api) -> None:
    created = post(api, "/api/sources", {**RUST_BLOG, "keywords": [" rust ", "", "  "]})
    assert created.json()["keywords"] == ["rust"]


def test_github_and_osv_sources_can_be_added_too(api: Api) -> None:
    assert (
        post(
            api, "/api/sources", {"name": "repos", "type": "github", "settings": {"repos": ["o/r"]}}
        ).status_code
        == 201
    )
    assert (
        post(api, "/api/sources", {"name": "cves", "type": "osv", "settings": {"since_days": 7}}).status_code
        == 201
    )
    assert [s["type"] for s in sources(api)] == ["github", "osv"]


# --- changing and removing ---


def test_a_source_is_replaced_whole_and_keeps_its_place_and_its_name(api: Api) -> None:
    post(api, "/api/sources", RUST_BLOG)
    post(api, "/api/sources", {**RUST_BLOG, "name": "second"})
    changed = api.client.put(
        "/api/sources/RUST-blog",
        json={
            "type": "rss",
            "settings": {"url": "https://example.com/other"},
            "channels": ["AI"],
            "keywords": ["llm"],
            "enabled": False,
        },
    )
    assert changed.status_code == 200
    first = changed.json()
    assert (first["name"], first["channels"], first["keywords"], first["enabled"]) == (
        "rust-blog",
        ["AI"],
        ["llm"],
        False,
    )
    assert [s["name"] for s in sources(api)] == ["rust-blog", "second"]


def test_a_change_is_validated_like_an_addition(api: Api) -> None:
    post(api, "/api/sources", RUST_BLOG)
    refused = api.client.put("/api/sources/rust-blog", json={"type": "rss", "settings": {"url": "nope"}})
    assert refused.status_code == 422
    assert sources(api)[0]["settings"] == {"url": FEED_URL}
    assert (
        api.client.put("/api/sources/ghost", json={"type": "rss", "settings": {"url": FEED_URL}}).status_code
        == 404
    )


def test_a_source_switched_off_is_not_fetched_and_on_again_it_is(api: Api) -> None:
    post(api, "/api/sources", RUST_BLOG)
    assert api.client.patch("/api/sources/rust-blog", json={"enabled": False}).json()["enabled"] is False
    api.run()
    assert api.items() == []
    assert api.client.patch("/api/sources/rust-blog", json={"enabled": True}).json()["enabled"] is True
    api.run()
    assert len(api.items()) == 3
    assert api.client.patch("/api/sources/ghost", json={"enabled": True}).status_code == 404


def test_deleting_a_source_keeps_its_items_and_forgets_its_history(api: Api) -> None:
    post(api, "/api/sources", RUST_BLOG)
    api.run()
    assert api.client.delete("/api/sources/rust-blog").status_code == 204
    assert sources(api) == []
    assert len(api.items()) == 3
    assert {i["sources"][0] for i in api.items()} == {"rust-blog"}
    assert api.client.delete("/api/sources/rust-blog").status_code == 404
    post(api, "/api/sources", RUST_BLOG)
    assert sources(api)[0]["items_seen"] == 0


# --- channels ---


def test_channels_can_be_added_described_and_removed(api: Api) -> None:
    created = post(api, "/api/channels", {"name": " Web ", "description": " Frontend "}).json()
    assert (created["name"], created["description"]) == ("Web", "Frontend")
    names = [c["name"] for c in api.client.get("/api/taxonomy").json()["channels"]]
    assert names == ["Rust", "AI", "Other", "Web"]
    assert (
        api.client.patch("/api/channels/web", json={"description": "Browsers"}).json()["description"]
        == "Browsers"
    )
    assert api.client.delete("/api/channels/WEB").status_code == 204
    assert "Web" not in [c["name"] for c in api.client.get("/api/taxonomy").json()["channels"]]


def test_channel_names_are_unique_ignoring_case_and_not_empty(api: Api) -> None:
    assert post(api, "/api/channels", {"name": "rust"}).status_code == 409
    assert post(api, "/api/channels", {"name": "  "}).status_code == 422
    assert api.client.patch("/api/channels/ghost", json={"description": "x"}).status_code == 404
    assert api.client.delete("/api/channels/ghost").status_code == 404


def test_a_channel_a_source_feeds_cannot_be_deleted_and_the_refusal_names_the_sources(api: Api) -> None:
    post(api, "/api/sources", RUST_BLOG)
    post(api, "/api/sources", {**RUST_BLOG, "name": "also-rust"})
    refused = api.client.delete("/api/channels/rust")
    assert refused.status_code == 409
    assert "rust-blog, also-rust" in refused.json()["detail"]
    api.client.delete("/api/sources/rust-blog")
    api.client.delete("/api/sources/also-rust")
    assert api.client.delete("/api/channels/Rust").status_code == 204


def test_other_always_exists(api: Api) -> None:
    refused = api.client.delete("/api/channels/other")
    assert refused.status_code == 409
    assert "always exists" in refused.json()["detail"]


# --- seeding ---


def test_the_file_seeds_sources_and_channels_once_and_then_the_database_is_the_truth(tmp_path: Path) -> None:
    lookout = Lookout(
        tmp_path, channels=[{"name": "Rust"}], sources=[{**RUST_BLOG, "settings": None, "url": FEED_URL}]
    )
    first = Api(lookout)
    try:
        assert [s["name"] for s in sources(first)] == ["rust-blog"]
        assert first.client.delete("/api/sources/rust-blog").status_code == 204
    finally:
        first.services.close()

    lookout.config["sources"].append({"name": "added-later", "type": "rss", "url": FEED_URL})
    lookout.config["channels"].append({"name": "Added"})
    lookout.write()
    second = Api(lookout)
    try:
        assert sources(second) == []
        assert "Added" not in [c["name"] for c in second.client.get("/api/taxonomy").json()["channels"]]
    finally:
        second.services.close()


def test_an_empty_file_still_counts_as_the_first_seeding(tmp_path: Path) -> None:
    lookout = Lookout(tmp_path, sources=[])
    first = Api(lookout)
    first.services.close()
    lookout.config["sources"] = [{"name": "late", "type": "rss", "url": FEED_URL}]
    lookout.write()
    second = Api(lookout)
    try:
        assert sources(second) == []
    finally:
        second.services.close()


def test_a_database_from_before_managed_sources_is_seeded_from_the_file_on_upgrade(tmp_path: Path) -> None:
    path = tmp_path / "lookout.db"
    with sqlite3.connect(path) as db:
        store.migrate_v1(db)
        store.migrate_v2(db)
        db.execute("PRAGMA user_version = 2")
    lookout = Lookout(tmp_path, sources=[{"name": "kept", "type": "rss", "url": FEED_URL}])
    upgraded = Api(lookout)
    try:
        assert [s["name"] for s in sources(upgraded)] == ["kept"]
        assert (tmp_path / "lookout.db.bak-v2").exists()
    finally:
        upgraded.services.close()


def test_a_seeded_source_with_bad_settings_stops_the_start_naming_it(tmp_path: Path) -> None:
    lookout = Lookout(tmp_path, sources=[{"name": "bad", "type": "rss", "url": "nope"}])
    with pytest.raises(ConfigError, match=r"source .bad. .rss.: .url. must start with http"):
        lookout.services()


def test_the_statuses_of_a_deleted_source_are_gone_from_the_database() -> None:
    db = database()
    statuses = SqliteSourceStatusRepository(db)
    statuses.save(SourceStatus("blog", items_seen=4))
    definitions = SqliteSourceDefinitions(db)
    definitions.save(SourceDef("blog", "rss", {"url": "https://x"}))
    definitions.delete("blog")
    assert statuses.get("blog").items_seen == 0


def test_other_is_added_when_the_file_declares_channels_without_it() -> None:
    db = database()
    registry = Registry(
        SqliteSourceDefinitions(db),
        SqliteChannelDefinitions(db),
        SqliteFlags(db),
        lambda _s: None,
        SqliteItemRepository(db),
    )
    registry.seed((), (Channel("AI"),))
    assert [c.name for c in registry.channels()] == ["AI", OTHER]
    registry.seed((), (Channel("AI"), Channel("Late")))
    assert [c.name for c in registry.channels()] == ["AI", OTHER]
