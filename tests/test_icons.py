"""Scenarios of openspec/specs/categories (An icon for each category)."""

import json
import re
import sqlite3
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
from tests.cli_support import Lookout, reading
from tests.test_http import Api

from lookout.adapters.store import sqlite as store
from lookout.adapters.store.sqlite import Database, SqliteChannelDefinitions
from lookout.domain.channel import clean_icon

CHANNELS = [{"name": "Dev"}, {"name": "Dev > Rust"}]
ICONS = {"Dev": "🛠️", "Dev > Rust": "🦀", "Other": "📦"}


@pytest.mark.parametrize("text", ["🦀", "🛠️", "👨‍👩‍👧", "🇫🇷", "★", " 🦀 ", "🧑🏽‍💻"])
def test_one_emoji_is_an_icon(text: str) -> None:
    assert clean_icon(text) == text.strip()


@pytest.mark.parametrize(
    "text",
    [
        "",
        "  ",
        "rust",
        "1",
        "🦀 rust",
        "<script>",
        "🦀<b>",
        "a🦀",
        "🦀🦀🦀🦀🦀🦀🦀🦀🦀🦀🦀🦀🦀",
        "\u200d",
        "&#x1f980;",
    ],
)
def test_text_markup_and_too_much_are_not_icons(text: str) -> None:
    assert clean_icon(text) == ""


class Iconist:
    """The model's side: answers icon questions from a table, counts them, reads everything else normally."""

    def __init__(self, answers: dict[str, str] | None = None) -> None:
        self.answers = answers or ICONS
        self.asked: list[str] = []

    def __call__(self, request: Any) -> str:
        body = request.content.decode()
        if "single emoji" not in body:
            return reading()
        name = re.search(r"Category: ([^\\\"]+)", body)
        assert name is not None
        self.asked.append(name.group(1))
        return json.dumps({"icon": self.answers.get(name.group(1), "")})


@pytest.fixture
def icons(tmp_path: Path) -> Iterator[tuple[Api, Iconist]]:
    instance = Api(Lookout(tmp_path, channels=CHANNELS))
    model = Iconist()
    instance.lookout.network.chat = model
    yield instance, model
    instance.services.close()


def shown(api: Api) -> dict[str, str]:
    return {c["name"]: c["icon"] for c in api.client.get("/api/taxonomy").json()["channels"]}


def test_a_run_gives_each_category_an_icon_once(icons: tuple[Api, Iconist]) -> None:
    api, model = icons

    api.run()
    api.run()

    assert shown(api) == ICONS
    assert sorted(model.asked) == ["Dev", "Dev > Rust", "Other"]


def test_an_answer_that_is_not_an_emoji_is_not_stored_and_not_asked_again(icons: tuple[Api, Iconist]) -> None:
    api, model = icons
    model.answers = {"Dev": "<script>", "Dev > Rust": "rust", "Other": "not json"}

    api.run()
    api.run()

    assert shown(api) == {"Dev": "", "Dev > Rust": "", "Other": ""}
    assert len(model.asked) == 3


def test_a_reply_that_is_not_json_or_not_an_object_gives_none(icons: tuple[Api, Iconist]) -> None:
    api, _ = icons
    api.lookout.network.chat = lambda request: (
        "oops" if "single emoji" in request.content.decode() else reading()
    )
    api.run()
    assert set(shown(api).values()) == {""}

    api.lookout.network.chat = lambda request: (
        "[1]" if "single emoji" in request.content.decode() else reading()
    )
    assert api.client.post("/api/channels/icons").json() == {"suggested": 0, "failed": False}


def test_suggest_icons_asks_again_for_the_categories_left_without(icons: tuple[Api, Iconist]) -> None:
    api, model = icons
    model.answers = {}
    api.run()
    assert set(shown(api).values()) == {""}

    model.answers = ICONS
    answer = api.client.post("/api/channels/icons").json()

    assert answer == {"suggested": 3, "failed": False}
    assert shown(api) == ICONS


def test_the_model_being_down_leaves_the_categories_for_the_next_try(icons: tuple[Api, Iconist]) -> None:
    api, _ = icons
    api.lookout.network.llm_down = True

    assert api.client.post("/api/channels/icons").json() == {"suggested": 0, "failed": True}
    assert set(shown(api).values()) == {""}

    api.lookout.network.llm_down = False
    api.run()
    assert shown(api) == ICONS


def test_an_icon_somebody_chose_is_never_replaced(icons: tuple[Api, Iconist]) -> None:
    api, model = icons
    assert api.client.patch("/api/channels/Dev", json={"icon": "🧰"}).json()["icon"] == "🧰"

    api.run()
    api.client.post("/api/channels/icons")

    assert shown(api)["Dev"] == "🧰"
    assert "Dev" not in model.asked


def test_the_user_sets_changes_and_clears_an_icon(icons: tuple[Api, Iconist]) -> None:
    api, model = icons
    api.client.patch("/api/channels/Dev", json={"description": "Code"})
    api.client.patch("/api/channels/Dev", json={"icon": "🧰"})
    after_description = api.client.patch("/api/channels/Dev", json={"description": "Code and tools"}).json()
    assert (after_description["description"], after_description["icon"]) == ("Code and tools", "🧰")

    cleared = api.client.patch("/api/channels/Dev", json={"icon": ""}).json()
    api.run()

    assert cleared["icon"] == ""
    assert shown(api)["Dev"] == ""
    assert "Dev" not in model.asked


@pytest.mark.parametrize("icon", ["abc", "<b>", "🦀🦀🦀🦀🦀🦀🦀🦀🦀🦀🦀🦀🦀"])
def test_a_text_icon_is_refused(icons: tuple[Api, Iconist], icon: str) -> None:
    api, _ = icons
    answer = api.client.patch("/api/channels/Dev", json={"icon": icon})
    assert (answer.status_code, answer.json()["detail"]) == (422, "an icon is one emoji")
    assert api.client.post("/api/channels", json={"name": "New", "icon": icon}).status_code == 422


def test_a_patch_must_change_something(icons: tuple[Api, Iconist]) -> None:
    api, _ = icons
    assert api.client.patch("/api/channels/Dev", json={}).status_code == 422


def test_a_new_category_may_bring_its_icon_and_keeps_it_when_moved(icons: tuple[Api, Iconist]) -> None:
    api, _ = icons
    created = api.client.post("/api/channels", json={"name": "Tools", "icon": "🔧"})
    assert created.json()["icon"] == "🔧"
    api.client.post("/api/channels", json={"name": "Quiet", "icon": ""})

    moved = api.client.post("/api/channels/Tools/move", json={"parent": "Dev"}).json()

    assert (moved["name"], moved["icon"]) == ("Dev > Tools", "🔧")
    assert shown(api)["Dev > Tools"] == "🔧"
    assert shown(api)["Quiet"] == ""


def test_a_category_declared_with_an_icon_starts_with_it(tmp_path: Path) -> None:
    api = Api(Lookout(tmp_path, channels=[{"name": "AI", "icon": "🤖"}]))
    try:
        api.lookout.network.chat = Iconist({"Other": "📦"})
        api.run()
        assert shown(api) == {"AI": "🤖", "Other": "📦"}
    finally:
        api.services.close()


def test_an_older_database_gets_the_icon_column_with_nothing_chosen(tmp_path: Path) -> None:
    path = tmp_path / "old.db"
    old = sqlite3.connect(path, isolation_level=None)
    for migrate in store.MIGRATIONS[:6]:
        migrate(old)
    old.execute("PRAGMA user_version = 6")
    old.execute("INSERT INTO channel_defs (name, description, position) VALUES ('Dev', 'Code', 1)")
    old.close()

    db = Database(path)
    try:
        assert [(c.name, c.description, c.icon) for c in SqliteChannelDefinitions(db).all()] == [
            ("Dev", "Code", None)
        ]
    finally:
        db.close()
