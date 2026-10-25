"""Scenarios of openspec/specs/digest."""

import json
import re
import sqlite3
from collections.abc import Callable, Iterator
from dataclasses import replace
from datetime import timedelta
from pathlib import Path
from typing import Any

import pytest
import yaml
from tests.cli_support import Lookout, reading
from tests.support import NOW, FixedClock, make_item, repository
from tests.test_http import Api

from lookout.adapters.store import sqlite as store
from lookout.adapters.store.sqlite import Database, SqliteDigestRepository
from lookout.application.digester import Digester, DigestError, DigestLimits, EmptyDigestError
from lookout.application.errors import ConfigError
from lookout.application.ports import InboxQuery
from lookout.bootstrap.container import load
from lookout.domain.digest import Digest, Point, Section
from lookout.domain.item import Item


def numbers(body: str) -> list[int]:
    return [int(n) for n in re.findall(r"\[(\d+)\] ", body)]


class Editor:
    """The digest model: writes one point per item (merging none), or whatever a test scripts."""

    def __init__(self) -> None:
        self.requests: list[dict[str, Any]] = []
        self.section: Callable[[list[int]], Any] = lambda nums: {
            "points": [{"text": f"Story {n}.", "items": [n]} for n in nums]
        }
        self.headline: Callable[[], Any] = lambda: {"headline": "Today: stories."}

    def __call__(self, request: Any) -> str:
        payload = json.loads(request.content)
        body = "\n".join(m["content"] for m in payload["messages"])
        if "news digest" not in body and "top of a news digest" not in body:
            return reading(channel="Dev" if "Django" in body else "Other")
        self.requests.append(payload)
        answer = self.headline() if "top of a news digest" in body else self.section(numbers(body))
        return answer if isinstance(answer, str) else json.dumps(answer)


@pytest.fixture
def world(tmp_path: Path) -> Iterator[tuple[Api, Editor]]:
    api = Api(Lookout(tmp_path, channels=[{"name": "Dev"}]))
    editor = Editor()
    api.lookout.network.chat = editor
    api.run()
    api.lookout.write()
    yield api, editor
    api.services.close()


def digest(api: Api, **filter_: Any) -> Any:
    return api.client.post("/api/digests", json={"filter": filter_})


def test_a_selection_becomes_sections_of_cited_points_with_a_headline(world: tuple[Api, Editor]) -> None:
    api, editor = world

    answer = digest(api)

    assert answer.status_code == 201
    out = answer.json()
    assert out["headline"] == "Today: stories."
    assert out["scope"] == "Inbox"
    assert [s["title"] for s in out["sections"]] == ["Dev", "Other"]
    dev, other = out["sections"]
    assert [p["text"] for p in dev["points"]] == ["Story 1."]
    assert [i["title"] for i in dev["points"][0]["items"]] == ["Django 6.0 released"]
    assert dev["points"][0]["items"][0]["url"] == "https://example.com/django-6?utm_source=rss"
    assert len(other["points"]) == 2
    assert (out["count"], out["total"], out["uncovered"]) == (3, 3, [])
    assert sorted(out["cited"]) == sorted(
        i["id"] for s in out["sections"] for p in s["points"] for i in p["items"]
    )
    assert len(editor.requests) == 3


def test_digests_are_kept_listed_opened_and_deleted(world: tuple[Api, Editor]) -> None:
    api, editor = world
    made = digest(api).json()
    calls = len(editor.requests)

    (listed,) = api.client.get("/api/digests").json()
    again = api.client.get(f"/api/digests/{made['id']}").json()

    assert (listed["id"], listed["headline"], listed["count"], listed["total"]) == (
        made["id"],
        "Today: stories.",
        3,
        3,
    )
    assert again == made
    assert len(editor.requests) == calls
    assert api.client.delete(f"/api/digests/{made['id']}").status_code == 204
    assert api.client.get("/api/digests").json() == []
    assert api.client.get(f"/api/digests/{made['id']}").status_code == 404
    assert api.client.delete(f"/api/digests/{made['id']}").status_code == 404


def test_the_scope_is_said_in_words(world: tuple[Api, Editor]) -> None:
    api, _ = world
    scope = digest(
        api,
        channel=["Dev"],
        priority=["P0", "P1", "P2", "P3"],
        source=["blog"],
        state=["new", "seen"],
        starred=False,
        text="django",
        newer_than_days=30,
    ).json()["scope"]
    assert scope == "Dev, P0, P1, P2, P3, from blog, new, seen, matching 'django', last 30 days"
    assert digest(api, older_than_days=0, starred=None).json()["scope"] == "older than 0 days"
    assert digest(api, starred=True).status_code == 422


def test_nothing_to_condense_keeps_nothing(world: tuple[Api, Editor]) -> None:
    api, editor = world
    answer = digest(api, text="no such words anywhere")
    assert (answer.status_code, answer.json()["detail"]) == (422, "nothing matches this selection")
    assert api.client.get("/api/digests").json() == []
    assert editor.requests == []


def test_a_citation_the_model_invented_is_dropped_and_uncited_items_are_listed(
    world: tuple[Api, Editor],
) -> None:
    api, editor = world
    editor.section = lambda nums: {
        "points": [
            {"text": "Cites a ghost and a real one.", "items": [99, nums[0], nums[0], 0, "1", True]},
            {"text": "Only a ghost.", "items": [99]},
            {"text": "", "items": [nums[0]]},
            {"text": "No list.", "items": "1"},
            "not an object",
        ]
    }

    out = digest(api).json()

    assert [[p["text"] for p in s["points"]] for s in out["sections"]] == [
        ["Cites a ghost and a real one."],
        ["Cites a ghost and a real one."],
    ]
    assert [len(p["items"]) for s in out["sections"] for p in s["points"]] == [1, 1]
    assert (out["count"], len(out["uncovered"])) == (3, 1)


def test_a_bad_answer_is_repaired_once(world: tuple[Api, Editor]) -> None:
    api, editor = world
    sent: list[str] = []
    good = editor.section

    def flaky(nums: list[int]) -> Any:
        sent.append("x")
        return "not json" if len(sent) == 1 else good(nums)

    editor.section = flaky

    assert digest(api).status_code == 201
    repair = [r for r in editor.requests if "That answer is invalid" in json.dumps(r)]
    assert len(repair) == 1


@pytest.mark.parametrize(
    "reply",
    ["not json", "[1]", json.dumps({"points": "nope"}), json.dumps({"points": []}), "<think>hmm</think>"],
)
def test_no_valid_answer_twice_fails_clearly_and_keeps_nothing(world: tuple[Api, Editor], reply: str) -> None:
    api, editor = world
    editor.section = lambda _nums: reply

    answer = digest(api)

    assert answer.status_code == 502
    assert (
        "the model could not write the digest: the model gave no valid answer twice"
        in answer.json()["detail"]
    )
    assert api.client.get("/api/digests").json() == []


def test_a_bad_headline_fails_too_and_thinking_is_not_part_of_an_answer(world: tuple[Api, Editor]) -> None:
    api, editor = world
    editor.section = lambda nums: (
        "<think>let me think</think>"
        + json.dumps({"points": [{"text": f"S{n}", "items": [n]} for n in nums]})
    )
    assert digest(api).status_code == 201

    editor.headline = lambda: {"headline": "  "}
    answer = digest(api)
    assert answer.status_code == 502
    assert "'headline' must be text" in answer.json()["detail"]


def test_the_model_being_down_fails_clearly(world: tuple[Api, Editor]) -> None:
    api, _ = world
    api.lookout.network.llm_down = True
    answer = digest(api)
    assert answer.status_code == 502
    assert "the model could not write the digest" in answer.json()["detail"]


def test_a_reply_without_content_or_an_http_error_is_a_failure(world: tuple[Api, Editor]) -> None:
    api, _ = world
    api.lookout.network.models = None
    api.lookout.network.chat = lambda _request: ""
    assert digest(api).status_code == 502


def test_the_digest_model_is_its_own_and_falls_back_to_the_reading_model(tmp_path: Path) -> None:
    (tmp_path / "a").mkdir()
    (tmp_path / "b").mkdir()
    own = Api(Lookout(tmp_path / "a", digest={"model": "big-one", "base_url": "http://localhost:11434/v1"}))
    plain = Api(Lookout(tmp_path / "b"))
    models: dict[str, set[str]] = {"own": set(), "plain": set()}
    try:
        for name, api in (("own", own), ("plain", plain)):
            editor = Editor()

            def seen(request: Any, name: str = name, editor: Editor = editor) -> str:
                models[name].add(json.loads(request.content)["model"])
                return editor(request)

            api.lookout.network.chat = seen
            api.run()
            assert digest(api).status_code == 201
        assert models == {"own": {"llama3.1", "big-one"}, "plain": {"llama3.1"}}
    finally:
        own.services.close()
        plain.services.close()


def test_a_category_too_big_for_the_context_is_written_in_parts() -> None:
    repo = repository()
    for n in range(5):
        repo.save(make_item(f"https://a.test/{n}", title=f"Story {n}", body="x" * 100, channel="Dev > Web"))

    class Writer:
        def __init__(self) -> None:
            self.calls: list[tuple[str, int]] = []

        def write_section(self, title: str, items: tuple[Item, ...]) -> tuple[Point, ...]:
            self.calls.append((title, len(items)))
            return (Point(f"{len(items)} items", tuple(i.id for i in items)),)

        def write_headline(self, sections: tuple[Section, ...]) -> str:
            return f"{len(sections)} sections"

    writer = Writer()
    kept = SqliteDigestRepository(Database(":memory:"))
    made = Digester(repo, writer, kept, FixedClock(), DigestLimits(max_items=4, context_chars=250)).create(
        InboxQuery(), "x"
    )

    assert writer.calls == [("Dev", 2), ("Dev", 2)]
    assert (made.count, made.total, made.headline) == (4, 5, "1 sections")
    assert kept.get(made.id) == made


def test_an_empty_selection_and_a_silent_model_are_errors() -> None:
    repo = repository()

    class Silent:
        def write_section(self, title: str, items: tuple[Item, ...]) -> tuple[Point, ...]:
            return ()

        def write_headline(self, sections: tuple[Section, ...]) -> str:
            raise AssertionError

    digester = Digester(repo, Silent(), SqliteDigestRepository(Database(":memory:")), FixedClock())
    with pytest.raises(EmptyDigestError):
        digester.create(InboxQuery(), "x")
    repo.save(make_item())
    with pytest.raises(DigestError, match="wrote nothing"):
        digester.create(InboxQuery(), "x")


def test_a_cited_item_that_is_gone_or_has_no_web_address_is_handled(world: tuple[Api, Editor]) -> None:
    api, _ = world
    odd = make_item("https://x.test/odd")
    odd = replace(odd, url="javascript:alert(1)")
    api.services.items.save(odd)
    gone = Digest(
        "abc123",
        NOW,
        "Inbox",
        "Head",
        (Section("Dev", (Point("Text", (odd.id, "missing-id")),)),),
        ("missing-id",),
        2,
    )
    api.services.digests.save(gone)

    out = api.client.get("/api/digests/abc123").json()

    (ref,) = out["sections"][0]["points"][0]["items"]
    assert (ref["id"], ref["url"]) == (odd.id, "")
    assert (out["uncovered"], out["cited"], out["count"]) == ([], [odd.id], 3)


def test_digests_come_newest_first_and_saving_again_replaces() -> None:
    kept = SqliteDigestRepository(Database(":memory:"))
    first = Digest("a", NOW, "s", "h", (Section("T", (Point("p", ("i",)),)),), (), 1)
    kept.save(first)
    kept.save(replace(first, id="b", created_at=NOW + timedelta(hours=1)))
    kept.save(replace(first, headline="changed"))

    assert [(d.id, d.headline) for d in kept.recent(10)] == [("b", "h"), ("a", "changed")]
    assert [d.id for d in kept.recent(1)] == ["b"]


def test_an_older_database_gets_the_digests_table(tmp_path: Path) -> None:
    old = sqlite3.connect(tmp_path / "old.db", isolation_level=None)
    for migrate in store.MIGRATIONS[:7]:
        migrate(old)
    old.execute("PRAGMA user_version = 7")
    old.close()

    db = Database(tmp_path / "old.db")
    try:
        assert SqliteDigestRepository(db).recent(5) == ()
    finally:
        db.close()


def test_the_digest_block_of_the_configuration_is_read_and_checked(tmp_path: Path) -> None:
    path = tmp_path / "lookout.yaml"
    path.write_text(yaml.safe_dump({"digest": {"model": "m", "max_items": 50, "context_chars": 9000}}))
    config = load(path, {})
    assert (config.digest.model, config.digest.max_items, config.digest.context_chars) == ("m", 50, 9000)
    assert (config.digest.base_url, load(tmp_path / "lookout.yaml", {}).digest.base_url) == ("", "")

    path.write_text(yaml.safe_dump({"digest": {"max_items": 0}}))
    with pytest.raises(ConfigError, match="max_items"):
        load(path, {})
