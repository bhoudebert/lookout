"""Scenarios of openspec/specs/digest."""

import json
import re
import sqlite3
from collections.abc import Callable, Iterator
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import httpx
import pytest
import yaml
from tests.cli_support import Lookout, http_client, reading
from tests.support import NOW, FixedClock, make_item, repository
from tests.test_http import Api

from lookout.adapters.http.app import create_app
from lookout.adapters.llm.openai_digest import OpenAiDigestWriter
from lookout.adapters.store import sqlite as store
from lookout.adapters.store.codec import decode_digest, encode_digest
from lookout.adapters.store.sqlite import Database, SqliteDigestRepository
from lookout.application.digest_jobs import DigestJobs, JobRunningError, JobState, UnknownJobError
from lookout.application.digester import (
    DigestCancelledError,
    Digester,
    DigestError,
    DigestLimits,
    EmptyDigestError,
    Unwatched,
)
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


def write(api: Api, **filter_: Any) -> tuple[dict[str, Any], dict[str, Any] | None]:
    """Ask for a digest (tests write it at once) and give the job and, if it worked, the digest."""
    api.lookout.clock.advance(minutes=1)
    started = api.client.post("/api/digests", json={"filter": filter_})
    assert started.status_code == 202
    job = next(j for j in api.client.get("/api/digests/jobs").json() if j["id"] == started.json()["id"])
    made = api.client.get(f"/api/digests/{job['digest_id']}").json() if job["digest_id"] else None
    return job, made


def digest(api: Api, **filter_: Any) -> dict[str, Any]:
    job, made = write(api, **filter_)
    assert made is not None, job["error"]
    return made


def failure(api: Api, **filter_: Any) -> str:
    job, made = write(api, **filter_)
    assert (job["state"], made) == ("failed", None)
    return str(job["error"])


# --- the digest ---------------------------------------------------------------------------------------


def test_a_selection_becomes_sections_of_cited_points_with_a_headline(world: tuple[Api, Editor]) -> None:
    api, editor = world

    out = digest(api)

    assert out["headline"] == "Today: stories."
    assert out["scope"] == "Inbox"
    assert [s["title"] for s in out["sections"]] == ["Dev", "Other"]
    dev, other = out["sections"]
    assert [p["text"] for p in dev["points"]] == ["Story 1."]
    assert [i["title"] for i in dev["points"][0]["items"]] == ["Django 6.0 released"]
    assert dev["points"][0]["items"][0]["url"] == "https://example.com/django-6?utm_source=rss"
    assert len(other["points"]) == 2
    assert (out["count"], out["total"], out["uncovered"]) == (3, 3, [])
    shown = [i["id"] for s in out["sections"] for p in s["points"] for i in p["items"]]
    assert sorted(out["cited"]) == sorted(shown)
    assert len(editor.requests) == 3


def test_the_model_is_asked_for_few_points_streamed_capped_and_without_thinking(
    world: tuple[Api, Editor],
) -> None:
    api, editor = world
    digest(api)

    section, _, headline = editor.requests
    assert section["stream"] is True
    assert (section["max_tokens"], headline["max_tokens"]) == (6144, 600)
    assert section["reasoning_effort"] == "none"
    assert "response_format" not in section
    prompt = section["messages"][0]["content"]
    assert "Group the items by story, theme or region" in prompt
    assert "write about 1 points" in prompt


def test_digests_are_kept_listed_opened_and_deleted(world: tuple[Api, Editor]) -> None:
    api, editor = world
    made = digest(api)
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
    assert api.client.get("/api/digests/jobs").json() == []
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
    )["scope"]
    assert scope == "Dev, P0, P1, P2, P3, from blog, new, seen, matching 'django', last 30 days"
    assert digest(api, older_than_days=0, starred=None)["scope"] == "older than 0 days"


def test_nothing_to_condense_fails_the_job_and_keeps_nothing(world: tuple[Api, Editor]) -> None:
    api, editor = world
    assert failure(api, text="no such words anywhere") == "nothing matches this selection"
    assert api.client.get("/api/digests").json() == []
    assert editor.requests == []


def test_a_citation_the_model_invented_is_dropped_and_uncited_items_are_listed(
    world: tuple[Api, Editor],
) -> None:
    api, editor = world
    calls: list[list[int]] = []

    def section(nums: list[int]) -> Any:
        calls.append(nums)
        if len(calls) > 2:  # the second try, for what the model left out, fails too
            return "not json"
        return {
            "points": [
                {"text": "Cites a ghost and a real one.", "items": [99, nums[0], nums[0], 0, "1", True]},
                {"text": "Only a ghost.", "items": [99]},
                {"text": "", "items": [nums[0]]},
                {"text": "No list.", "items": "1"},
                "not an object",
            ]
        }

    editor.section = section

    out = digest(api)

    assert [[p["text"] for p in s["points"]] for s in out["sections"]] == [
        ["Cites a ghost and a real one."],
        ["Cites a ghost and a real one."],
    ]
    assert [len(p["items"]) for s in out["sections"] for p in s["points"]] == [1, 1]
    assert (out["count"], len(out["uncovered"])) == (3, 1)


def test_an_answer_in_a_code_fence_or_a_sentence_is_read(world: tuple[Api, Editor]) -> None:
    api, editor = world
    editor.section = lambda nums: (
        "Here you go:\n```json\n"
        + json.dumps({"points": [{"text": "Fenced.", "items": [nums[0]]}]})
        + "\n```"
    )
    assert digest(api)["sections"][0]["points"][0]["text"] == "Fenced."


def test_a_bad_answer_is_repaired_once(world: tuple[Api, Editor]) -> None:
    api, editor = world
    sent: list[str] = []
    good = editor.section

    def flaky(nums: list[int]) -> Any:
        sent.append("x")
        return "not json" if len(sent) == 1 else good(nums)

    editor.section = flaky

    assert digest(api)["count"] == 3
    assert len([r for r in editor.requests if "That answer is invalid" in json.dumps(r)]) == 1


@pytest.mark.parametrize(
    "reply",
    ["not json", "[1]", json.dumps({"points": "nope"}), json.dumps({"points": []}), "<think>hmm</think>"],
)
def test_no_valid_answer_twice_fails_clearly_and_keeps_nothing(world: tuple[Api, Editor], reply: str) -> None:
    api, editor = world
    editor.section = lambda _nums: reply

    error = failure(api)

    assert "the model gave no valid answer twice" in error
    assert api.client.get("/api/digests").json() == []


def test_a_bad_headline_fails_too_and_thinking_is_not_part_of_an_answer(world: tuple[Api, Editor]) -> None:
    api, editor = world
    editor.section = lambda nums: (
        "<think>let me think</think>"
        + json.dumps({"points": [{"text": f"S{n}", "items": [n]} for n in nums]})
    )
    assert digest(api)["count"] == 3

    editor.headline = lambda: {"headline": "  "}
    assert "'headline' must be text" in failure(api)


def test_the_model_being_down_fails_clearly(world: tuple[Api, Editor]) -> None:
    api, _ = world
    api.lookout.network.llm_down = True
    assert "connection refused" in failure(api)


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
            digest(api)
        assert models == {"own": {"llama3.1", "big-one"}, "plain": {"llama3.1"}}
    finally:
        own.services.close()
        plain.services.close()


def test_the_reasoning_effort_and_the_answer_limit_come_from_the_configuration(tmp_path: Path) -> None:
    api = Api(Lookout(tmp_path, digest={"reasoning_effort": "", "max_answer_tokens": 300}))
    editor = Editor()
    api.lookout.network.chat = editor
    try:
        api.run()
        digest(api)
        section, *_ = editor.requests
        assert "reasoning_effort" not in section
        assert section["max_tokens"] == 300
    finally:
        api.services.close()


# --- the model's side: stream, limit, thinking --------------------------------------------------------


class Watcher:
    """Follows a writer: counts what it wrote, and says stop after a number of tokens."""

    def __init__(self, stop_after: int | None = None) -> None:
        self.tokens = 0
        self.stop_after = stop_after

    def planned(self, sections: int) -> None: ...

    def selected(self, count: int, since: datetime, until: datetime) -> None: ...

    def started(self, title: str) -> None: ...

    def wrote(self, tokens: int) -> None:
        self.tokens += tokens

    def stopped(self) -> bool:
        return self.stop_after is not None and self.tokens >= self.stop_after


def sse(*deltas: dict[str, Any], finish: str = "stop") -> bytes:
    events: list[dict[str, Any]] = [{"choices": [{"delta": d, "finish_reason": None}]} for d in deltas]
    events.append({"choices": [{"delta": {}, "finish_reason": finish}]})
    return ("\n".join(f"data: {json.dumps(e)}\n" for e in events) + "\n: comment\ndata: [DONE]\n").encode()


def writer_over(body: bytes | int, **kw: Any) -> OpenAiDigestWriter:
    def answer(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(body) if isinstance(body, int) else httpx.Response(200, content=body)

    client = httpx.Client(transport=httpx.MockTransport(answer))
    return OpenAiDigestWriter(client, base_url="http://x/v1/", model="m", **kw)


ITEMS = (make_item("https://a.test/1", title="One"), make_item("https://a.test/2", title="Two"))
GOOD = json.dumps({"points": [{"text": "T", "items": [1]}]})


def test_a_writer_reads_the_stream_and_counts_what_the_model_writes() -> None:
    watch = Watcher()
    body = sse({"content": GOOD[:10]}, {"content": GOOD[10:]}, {"reasoning": "hmm"}, {"content": ""})

    points = writer_over(body, api_key="k").write_section("News", ITEMS, watch)

    assert [(p.text, p.items) for p in points] == [("T", (ITEMS[0].id,))]
    assert watch.tokens == 3


def test_a_model_that_hits_the_limit_while_thinking_says_so() -> None:
    watch = Watcher()
    body = sse({"reasoning": "a"}, {"reasoning_content": "b"}, finish="length")

    with pytest.raises(DigestError, match=r"limit of 50 tokens without answering, it kept thinking"):
        writer_over(body, max_answer_tokens=50).write_section("News", ITEMS, watch)
    assert watch.tokens == 2


def test_a_model_that_hits_the_limit_while_answering_says_so() -> None:
    body = sse({"content": '{"points": [{"text"'}, finish="length")
    with pytest.raises(DigestError, match=r"limit of 60 tokens$"):
        writer_over(body, max_answer_tokens=60).write_section("News", ITEMS, Watcher())


def test_a_writer_stops_reading_when_told_to_stop() -> None:
    watch = Watcher(stop_after=1)
    body = sse({"content": "x"}, {"content": "y"}, {"content": "z"})
    with pytest.raises(DigestCancelledError):
        writer_over(body).write_headline((Section("S", (Point("p", ("i",)),)),), watch)
    assert watch.tokens == 1


@pytest.mark.parametrize("body", [503, b"data: {not json}\n", b'data: {"choices": []}\n'])
def test_a_server_error_or_a_garbled_stream_is_a_failure(body: bytes | int) -> None:
    with pytest.raises(DigestError):
        writer_over(body).write_section("News", ITEMS, Watcher())


def test_a_writer_merges_points_citing_the_points_it_merges_and_keeps_the_ones_it_forgot() -> None:
    points = (
        Point("One", (ITEMS[0].id,)),
        Point("Two", (ITEMS[1].id,)),
        Point("Three", ("third",)),
    )
    answer = json.dumps(
        {
            "points": [
                {"text": "One and two", "items": [1, 2, 2, 99, "x"]},
                {"text": "", "items": [3]},
                {"text": "no list", "items": 3},
                "not an object",
            ]
        }
    )

    merged = writer_over(sse({"content": answer})).merge_points("News", points, Watcher())

    assert [(p.text, p.items) for p in merged] == [
        ("One and two", (ITEMS[0].id, ITEMS[1].id)),
        ("Three", ("third",)),
    ]


@pytest.mark.parametrize(
    "answer", ["{}", '{"points": "x"}', '{"points": [{"text": "T", "items": [9]}]}', "nope"]
)
def test_a_merge_that_cites_nothing_is_a_failure(answer: str) -> None:
    with pytest.raises(DigestError, match="no valid answer twice"):
        writer_over(sse({"content": answer})).merge_points("News", (Point("One", ("a",)),), Watcher())


@pytest.mark.parametrize(
    "answer",
    [
        '{"points": [{"text": "T", "items": [1]}]',
        '{"points": [{"text": "T", "items": [1]}',
        '```json\n{"points": [{"text": "T", "items": [1]}]}\n```',
    ],
)
def test_an_answer_missing_its_closing_brackets_or_fenced_is_read(answer: str) -> None:
    (point,) = writer_over(sse({"content": answer})).write_section("News", ITEMS, Watcher())
    assert (point.text, point.items) == ("T", (ITEMS[0].id,))


# --- the use case -------------------------------------------------------------------------------------


class ChunkWriter:
    def __init__(self) -> None:
        self.calls: list[tuple[str, int]] = []
        self.merged: list[int] = []

    def write_section(self, title: str, items: tuple[Item, ...], watch: Any) -> tuple[Point, ...]:
        self.calls.append((title, len(items)))
        return (Point(f"{len(items)} items", tuple(i.id for i in items)),)

    def merge_points(self, title: str, points: tuple[Point, ...], watch: Any) -> tuple[Point, ...]:
        self.merged.append(len(points))
        return (Point("merged", tuple(i for p in points for i in p.items)),)

    def write_headline(self, sections: tuple[Section, ...], watch: Any) -> str:
        return f"{len(sections)} sections"


def test_a_category_too_big_for_the_context_is_written_in_parts() -> None:
    repo = repository()
    for n in range(5):
        repo.save(make_item(f"https://a.test/{n}", title=f"Story {n}", body="x" * 100, channel="Dev > Web"))
    writer = ChunkWriter()
    kept = SqliteDigestRepository(Database(":memory:"))
    limits = DigestLimits(max_items=4, context_chars=250)

    made = Digester(repo, writer, kept, FixedClock(), limits).create(InboxQuery(), "x")

    assert writer.calls == [("Dev", 2), ("Dev", 2)]
    assert writer.merged == [2]
    assert [(len(s.points), len(s.points[0].items)) for s in made.sections] == [(1, 4)]
    assert (made.count, made.total, made.headline) == (4, 5, "1 sections")
    assert kept.get(made.id) == made


def test_a_category_is_written_in_calls_of_a_few_items_and_their_points_merged() -> None:
    repo = repository()
    for n in range(5):
        repo.save(make_item(f"https://a.test/{n}", title=f"Story {n}", channel="Dev"))
    writer = ChunkWriter()

    made = Digester(
        repo,
        writer,
        SqliteDigestRepository(Database(":memory:")),
        FixedClock(),
        DigestLimits(items_per_call=2),
    ).create(InboxQuery(), "x")

    assert writer.calls == [("Dev", 2), ("Dev", 2), ("Dev", 1)]
    assert (writer.merged, made.count) == ([3], 5)


def test_points_that_cannot_be_merged_are_kept_as_written() -> None:
    repo = repository()
    for n in range(4):
        repo.save(make_item(f"https://a.test/{n}", title=f"Story {n}", channel="Dev"))

    class NoMerge(ChunkWriter):
        def merge_points(self, title: str, points: tuple[Point, ...], watch: Any) -> tuple[Point, ...]:
            raise DigestError("cannot merge")

    made = Digester(
        repo,
        NoMerge(),
        SqliteDigestRepository(Database(":memory:")),
        FixedClock(),
        DigestLimits(items_per_call=2),
    ).create(InboxQuery(), "x")

    assert [len(s.points) for s in made.sections] == [2]
    assert made.uncovered == ()


def test_items_the_model_leaves_out_are_asked_about_once_more() -> None:
    repo = repository()
    for n in range(4):
        repo.save(make_item(f"https://a.test/{n}", title=f"Story {n}", channel="Dev"))

    class Lazy(ChunkWriter):
        def write_section(self, title: str, items: tuple[Item, ...], watch: Any) -> tuple[Point, ...]:
            self.calls.append((title, len(items)))
            kept = items[:1] if len(self.calls) == 1 else items
            return tuple(Point(i.title, (i.id,)) for i in kept)

    writer = Lazy()
    kept = SqliteDigestRepository(Database(":memory:"))

    made = Digester(repo, writer, kept, FixedClock()).create(InboxQuery(), "x")

    assert writer.calls == [("Dev", 4), ("Dev", 3)]
    assert (made.count, made.uncovered) == (4, ())
    assert len(made.cited) == 4


def test_items_still_left_out_after_the_second_try_are_listed_not_covered() -> None:
    repo = repository()
    for n in range(3):
        repo.save(make_item(f"https://a.test/{n}", title=f"Story {n}", channel="Dev"))

    class Stubborn(ChunkWriter):
        def write_section(self, title: str, items: tuple[Item, ...], watch: Any) -> tuple[Point, ...]:
            self.calls.append((title, len(items)))
            if len(self.calls) > 1:
                raise DigestError("the model is on strike")
            return (Point("Only one", (items[0].id,)),)

    writer = Stubborn()
    made = Digester(repo, writer, SqliteDigestRepository(Database(":memory:")), FixedClock()).create(
        InboxQuery(), "x"
    )

    assert writer.calls == [("Dev", 3), ("Dev", 2)]
    assert (len(made.cited), len(made.uncovered)) == (1, 2)


def test_an_empty_selection_and_a_silent_model_are_errors() -> None:
    repo = repository()

    class Silent(ChunkWriter):
        def write_section(self, title: str, items: tuple[Item, ...], watch: Any) -> tuple[Point, ...]:
            return ()

    digester = Digester(repo, Silent(), SqliteDigestRepository(Database(":memory:")), FixedClock())
    with pytest.raises(EmptyDigestError):
        digester.create(InboxQuery(), "x")
    repo.save(make_item())
    with pytest.raises(DigestError, match="wrote nothing"):
        digester.create(InboxQuery(), "x")


def test_a_digest_stopped_after_its_sections_does_not_write_the_headline() -> None:
    class StopOnSecondLook(Watcher):
        def __init__(self) -> None:
            super().__init__()
            self.looks = 0

        def stopped(self) -> bool:
            self.looks += 1
            return self.looks >= 2

    repo = repository()
    repo.save(make_item("https://a.test/1", title="One", channel="Dev"))
    writer = ChunkWriter()
    kept = SqliteDigestRepository(Database(":memory:"))

    with pytest.raises(DigestCancelledError):
        Digester(repo, writer, kept, FixedClock()).create(InboxQuery(), "x", StopOnSecondLook())

    assert writer.calls == [("Dev", 1)]
    assert kept.recent(5) == ()


def test_nobody_watching_never_stops_a_digest() -> None:
    assert Unwatched().stopped() is False
    Unwatched().planned(2)
    Unwatched().started("x")
    Unwatched().wrote(1)


# --- written in the background ------------------------------------------------------------------------


def jobs_over(writer: Any, repo: Any = None) -> tuple[DigestJobs, list[Callable[[], None]], FixedClock]:
    items = repo or repository()
    if repo is None:
        items.save(make_item("https://a.test/1", title="One", channel="Dev"))
        items.save(make_item("https://a.test/2", title="Two", channel="Other"))
    clock = FixedClock()
    digester = Digester(items, writer, SqliteDigestRepository(Database(":memory:")), clock)
    later: list[Callable[[], None]] = []
    return DigestJobs(digester, clock, spawn=later.append), later, clock


def test_a_job_shows_its_progress_while_it_is_written_and_its_digest_when_done() -> None:
    seen: list[Any] = []

    class Slow(ChunkWriter):
        def __init__(self, jobs: Callable[[], Any]) -> None:
            super().__init__()
            self.jobs = jobs

        def write_section(self, title: str, items: tuple[Item, ...], watch: Any) -> tuple[Point, ...]:
            watch.wrote(5)
            seen.append(self.jobs()[0])
            return super().write_section(title, items, watch)

    holder: dict[str, DigestJobs] = {}
    writer = Slow(lambda: holder["jobs"].jobs())  # noqa: PLW0108
    jobs, later, _ = jobs_over(writer)
    holder["jobs"] = jobs

    started, was_started = jobs.start(InboxQuery(), "Inbox")
    assert (was_started, started.state) == (True, JobState.RUNNING)
    assert jobs.jobs() == (started,)
    later.pop()()

    assert [(j.section, j.section_number, j.sections_total, j.tokens) for j in seen] == [
        ("Dev", 1, 3, 5),
        ("Other", 2, 3, 10),
    ]
    (done,) = jobs.jobs()
    assert (done.state, done.section, done.section_number, done.error) == (JobState.DONE, "Headline", 3, None)
    assert done.digest_id is not None
    assert done.finished_at is not None


def test_only_one_digest_is_written_at_a_time() -> None:
    jobs, later, clock = jobs_over(ChunkWriter())
    first, _ = jobs.start(InboxQuery(), "Inbox")

    again, started = jobs.start(InboxQuery(), "Something else")

    assert (again, started, len(later)) == (first, False, 1)
    later.pop()()
    clock.advance(minutes=1)
    assert jobs.start(InboxQuery(), "Something else")[1] is True


def test_a_job_can_be_cancelled_and_stops_before_writing() -> None:
    writer = ChunkWriter()
    jobs, later, _ = jobs_over(writer)
    job, _ = jobs.start(InboxQuery(), "Inbox")

    assert jobs.cancel(job.id).state is JobState.RUNNING
    later.pop()()

    (stopped,) = jobs.jobs()
    assert (stopped.state, stopped.error, stopped.digest_id) == (JobState.CANCELLED, None, None)
    assert writer.calls == []
    assert jobs.cancel(job.id).state is JobState.CANCELLED
    with pytest.raises(UnknownJobError):
        jobs.cancel("nope")


def test_a_failed_job_keeps_its_reason_until_dismissed() -> None:
    class Failing(ChunkWriter):
        def write_section(self, title: str, items: tuple[Item, ...], watch: Any) -> tuple[Point, ...]:
            raise DigestError("the model is on strike")

    class Crashing(ChunkWriter):
        def write_section(self, title: str, items: tuple[Item, ...], watch: Any) -> tuple[Point, ...]:
            raise ZeroDivisionError("oops")

    for writer, reason in ((Failing(), "the model is on strike"), (Crashing(), "ZeroDivisionError: oops")):
        jobs, later, _ = jobs_over(writer)
        job, _ = jobs.start(InboxQuery(), "Inbox")
        with pytest.raises(JobRunningError):
            jobs.dismiss(job.id)
        later.pop()()
        (failed,) = jobs.jobs()
        assert (failed.state, failed.error) == (JobState.FAILED, reason)
        jobs.dismiss(job.id)
        assert jobs.jobs() == ()
        with pytest.raises(UnknownJobError):
            jobs.dismiss(job.id)


def test_only_the_latest_finished_jobs_are_remembered_and_the_running_one_comes_first() -> None:
    jobs, later, clock = jobs_over(ChunkWriter())
    for n in range(12):
        clock.advance(minutes=1)
        jobs.start(InboxQuery(), f"digest {n}")
        later.pop()()
    clock.advance(minutes=1)
    running, _ = jobs.start(InboxQuery(), "now")

    listed = jobs.jobs()

    assert len(listed) == 11
    assert listed[0] == running
    assert [j.scope for j in listed[1:3]] == ["digest 11", "digest 10"]


def test_the_api_follows_a_digest_job_and_cancels_or_dismisses_it(world: tuple[Api, Editor]) -> None:
    api, _ = world
    deferred: list[Callable[[], None]] = []
    api.services = replace(
        api.services, digest_jobs=DigestJobs(api.services.digester, api.lookout.clock, spawn=deferred.append)
    )
    client = http_client(create_app(api.services))

    first = client.post("/api/digests", json={}).json()
    second = client.post("/api/digests", json={}).json()
    assert (first["started"], second["started"], second["id"]) == (True, False, first["id"])
    assert client.delete(f"/api/digests/jobs/{first['id']}").status_code == 409
    assert client.post(f"/api/digests/jobs/{first['id']}/cancel").json()["state"] == "running"
    deferred.pop()()

    (job,) = client.get("/api/digests/jobs").json()
    assert (job["state"], job["error"], job["tokens"]) == ("cancelled", None, 0)
    assert client.post("/api/digests/jobs/zzz/cancel").status_code == 404
    assert client.delete("/api/digests/jobs/zzz").status_code == 404
    assert client.delete(f"/api/digests/jobs/{first['id']}").status_code == 204
    assert client.get("/api/digests/jobs").json() == []


def test_a_job_reports_the_tokens_the_model_wrote(world: tuple[Api, Editor]) -> None:
    api, _ = world
    job, _ = write(api)
    assert (job["state"], job["section"], job["section_number"], job["sections_total"]) == (
        "done",
        "Headline",
        3,
        3,
    )
    assert job["tokens"] > 0


def test_a_digest_and_its_job_say_when_the_items_they_cover_were_published(world: tuple[Api, Editor]) -> None:
    api, _ = world
    dates = sorted(i.published_at for i in api.services.items.search(InboxQuery(limit=50)).items)
    job, made = write(api)

    assert made is not None
    (listed,) = api.client.get("/api/digests").json()
    expected = (_iso(dates[0]), _iso(dates[-1]))
    assert job["count"] == 3
    for shown in (job, made, listed):
        assert (_iso_text(shown["since"]), _iso_text(shown["until"])) == expected


def test_a_digest_kept_before_dates_were_known_reads_without_them() -> None:
    kept = SqliteDigestRepository(Database(":memory:"))
    old = json.loads(encode_digest(Digest("a", NOW, "s", "h", (Section("T", (Point("p", ("i",)),)),), (), 1)))
    del old["since"], old["until"]

    read = decode_digest(json.dumps(old))
    kept.save(read)

    assert (read.since, read.until) == (None, None)
    assert kept.get("a") == read


def _iso(moment: Any) -> str:
    return _iso_text(moment.isoformat())


def _iso_text(text: str) -> str:
    return datetime.fromisoformat(text.replace("Z", "+00:00")).astimezone(UTC).isoformat()


# --- keeping and migrating ----------------------------------------------------------------------------


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
    path.write_text(
        yaml.safe_dump(
            {
                "digest": {
                    "model": "m",
                    "max_items": 50,
                    "context_chars": 9000,
                    "max_answer_tokens": 999,
                    "items_per_call": 7,
                    "reasoning_effort": "low",
                }
            }
        )
    )
    config = load(path, {})
    assert (config.digest.model, config.digest.max_items, config.digest.context_chars) == ("m", 50, 9000)
    assert (config.digest.max_answer_tokens, config.digest.reasoning_effort) == (999, "low")
    assert config.digest.items_per_call == 7
    assert (config.digest.base_url, load(tmp_path / "lookout.yaml", {}).digest.base_url) == ("", "")

    path.write_text(yaml.safe_dump({"digest": {"max_items": 0}}))
    with pytest.raises(ConfigError, match="max_items"):
        load(path, {})
    path.write_text(yaml.safe_dump({"digest": {"items_per_call": 1}}))
    with pytest.raises(ConfigError, match="items_per_call"):
        load(path, {})
    path.write_text(yaml.safe_dump({"digest": {"max_answer_tokens": 10}}))
    with pytest.raises(ConfigError, match="max_answer_tokens"):
        load(path, {})
