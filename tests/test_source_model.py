"""Scenarios of openspec/specs/enrichment: a model of its own for a source."""

import json
import sqlite3
from pathlib import Path
from typing import Any

import httpx
from tests.cli_support import FEED_URL, Lookout, reading
from tests.support import ScriptedEnricher, database, make_item
from tests.test_enrich import build
from tests.test_http import Api

from lookout.adapters.store import sqlite as store
from lookout.adapters.store.sqlite import Database, SqliteSourceDefinitions
from lookout.application.enrich import Enrich, OwnModels
from lookout.application.ports_sources import Enricher
from lookout.bootstrap.container import load
from lookout.domain.policy import PriorityPolicy
from lookout.domain.source import SourceDef


def two_models() -> tuple[Enrich, ScriptedEnricher, ScriptedEnricher, Any]:
    default, french = ScriptedEnricher(), ScriptedEnricher()
    _, items, usage, clock = build(default)
    asked: list[str] = []

    def readers(model: str) -> Enricher:
        asked.append(model)
        return french

    reader = Enrich(
        items,
        default,
        usage,
        clock,
        PriorityPolicy(),
        daily_limit=10,
        own_models=OwnModels(lambda: {"dealabs": "qwen3:8b"}, readers),
    )
    return reader, default, french, (items, asked)


def test_a_source_with_a_model_is_read_by_it_and_the_others_by_the_default() -> None:
    reader, default, french, (items, asked) = two_models()
    items.save(make_item("https://a.test/1", title="Promo", sources=("dealabs",)))
    items.save(make_item("https://a.test/2", title="News", sources=("blog",)))
    items.save(make_item("https://a.test/3", title="Both", sources=("blog", "dealabs")))

    assert reader.run().enriched == 3

    assert sorted(french.asked) == ["Both", "Promo"]
    assert default.asked == ["News"]
    assert set(asked) == {"qwen3:8b"}


def test_a_source_keeps_its_model_in_the_database_and_older_databases_get_the_column(tmp_path: Path) -> None:
    kept = SqliteSourceDefinitions(database())
    kept.save(SourceDef("fr", "rss", model="qwen3:8b"))
    kept.save(SourceDef("en", "rss"))
    assert {s.name: s.model for s in kept.all()} == {"fr": "qwen3:8b", "en": ""}

    old = sqlite3.connect(tmp_path / "old.db", isolation_level=None)
    for migrate in store.MIGRATIONS[:8]:
        migrate(old)
    old.execute("PRAGMA user_version = 8")
    old.execute(
        "INSERT INTO source_defs VALUES ('x', 'rss', '{}', '[]', '[]', 1, 1)",
    )
    old.close()
    db = Database(tmp_path / "old.db")
    try:
        assert [s.model for s in SqliteSourceDefinitions(db).all()] == [""]
    finally:
        db.close()


def test_the_configuration_gives_a_source_its_model_and_the_readers_their_reasoning_effort(
    tmp_path: Path,
) -> None:
    path = tmp_path / "lookout.yaml"
    path.write_text(
        "llm: {reasoning_effort: none}\n"
        f"sources:\n  - {{name: fr, type: rss, url: '{FEED_URL}', model: qwen3:8b}}\n"
        f"  - {{name: en, type: rss, url: '{FEED_URL}'}}\n"
    )
    config = load(path, {})
    assert [(s.name, s.model) for s in config.sources] == [("fr", "qwen3:8b"), ("en", "")]
    assert all("model" not in s.settings for s in config.sources)
    assert config.llm.reasoning_effort == "none"


def test_the_api_sets_shows_and_clears_the_model_of_a_source(tmp_path: Path) -> None:
    api = Api(Lookout(tmp_path, sources=[], channels=[{"name": "Dev"}]))
    try:
        body = {"name": "fr", "type": "rss", "settings": {"url": FEED_URL}, "model": "  qwen3:8b "}
        assert api.client.post("/api/sources", json=body).json()["model"] == "qwen3:8b"
        assert api.services.registry.models() == {"fr": "qwen3:8b"}
        listed = api.client.get("/api/sources").json()
        assert [(s["name"], s["model"]) for s in listed] == [("fr", "qwen3:8b")]

        cleared = api.client.put("/api/sources/fr", json={"type": "rss", "settings": {"url": FEED_URL}})
        assert cleared.json()["model"] == ""
        assert api.services.registry.models() == {}
    finally:
        api.services.close()


def test_a_run_reads_each_source_with_its_own_model_and_sends_the_reasoning_effort(tmp_path: Path) -> None:
    lookout = Lookout(
        tmp_path,
        llm={"model": "default-model", "reasoning_effort": "none"},
        sources=[{"name": "blog", "type": "rss", "url": FEED_URL, "model": "own-model"}],
    )
    seen: list[dict[str, Any]] = []

    def chat(request: httpx.Request) -> str:
        seen.append(json.loads(request.content))
        return reading()

    lookout.network.chat = chat
    api = Api(lookout)
    try:
        api.run()
        assert seen
        # The source's items are read by its model; only the category icons are asked of the default one.
        assert "own-model" in {p["model"] for p in seen}
        assert all("icon" in p["messages"][0]["content"] for p in seen if p["model"] == "default-model")
        assert {p["reasoning_effort"] for p in seen} == {"none"}
    finally:
        api.services.close()
