"""Scenarios of openspec/specs/source-ingestion: Hacker News."""

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx
import pytest
import yaml
from tests.cli_support import FEED_URL, Lookout

from lookout.adapters.sources.hackernews import API, HackerNewsFetcher
from lookout.application.errors import ConfigError
from lookout.application.ports_sources import SourceError
from lookout.bootstrap.container import build, load

HITS = {
    "hits": [
        {
            "objectID": "1",
            "title": "Rust 1.99 released",
            "url": "https://blog.rust-lang.org/1.99",
            "author": "steve",
            "points": 420,
            "num_comments": 87,
            "created_at_i": 1_790_000_000,
        },
        {
            "objectID": "2",
            "title": "Ask HN: how do you triage feeds?",
            "url": None,
            "author": "alice",
            "points": None,
            "num_comments": None,
            "story_text": "<p>I follow too many.</p>",
            "created_at_i": None,
        },
        {"objectID": "3", "title": "", "url": "https://x.test"},
        {"title": "no id", "url": "https://y.test"},
    ]
}


class Algolia:
    """The search API, scripted; remembers what was asked."""

    def __init__(self, answer: httpx.Response | None = None) -> None:
        self.answer = answer or httpx.Response(200, json=HITS)
        self.requests: list[httpx.Request] = []

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        return self.answer

    def fetcher(self, **kw: Any) -> HackerNewsFetcher:
        return HackerNewsFetcher("hn", httpx.Client(transport=httpx.MockTransport(self)), **kw)


def test_stories_become_items_with_their_points_and_the_discussion_link() -> None:
    first, second = Algolia().fetcher().fetch()
    assert (first.url, first.title, first.author) == (
        "https://blog.rust-lang.org/1.99",
        "Rust 1.99 released",
        "steve",
    )
    assert first.published_at == datetime.fromtimestamp(1_790_000_000, UTC)
    assert "420 points and 87 comments on Hacker News: https://news.ycombinator.com/item?id=1" in first.body
    assert first.tags == ()
    # An Ask HN has no address of its own: the discussion is the item, and its text is kept.
    assert second.url == "https://news.ycombinator.com/item?id=2"
    assert second.body.startswith("<p>I follow too many.</p>")
    assert "0 points and 0 comments" in second.body
    assert second.published_at is None


@pytest.mark.parametrize(
    ("feed", "path", "tag", "label"),
    [
        ("front_page", "search", "front_page", ()),
        ("newest", "search_by_date", "story", ()),
        ("ask", "search_by_date", "ask_hn", ("ask-hn",)),
        ("show", "search_by_date", "show_hn", ("show-hn",)),
    ],
)
def test_each_list_asks_for_its_own_stories(feed: str, path: str, tag: str, label: tuple[str, ...]) -> None:
    algolia = Algolia()
    raws = algolia.fetcher(feed=feed, limit=10).fetch()
    request = algolia.requests[0]
    assert str(request.url).startswith(f"{API}/{path}?")
    assert (request.url.params["tags"], request.url.params["hitsPerPage"]) == (tag, "10")
    assert "numericFilters" not in request.url.params
    assert all(r.tags == label for r in raws)


def test_a_minimum_of_points_is_asked_of_the_service() -> None:
    algolia = Algolia()
    algolia.fetcher(min_points=100).fetch()
    assert algolia.requests[0].url.params["numericFilters"] == "points>=100"


def test_keywords_keep_only_matching_stories() -> None:
    raws = Algolia().fetcher(keywords=("RUST",)).fetch()
    assert [r.title for r in raws] == ["Rust 1.99 released"]


@pytest.mark.parametrize(
    "answer",
    [
        httpx.Response(503),
        httpx.Response(200, content=b"<html>"),
        httpx.Response(200, json={"nope": []}),
        httpx.Response(200, json=[1]),
    ],
)
def test_a_service_that_fails_or_answers_junk_is_a_source_error(answer: httpx.Response) -> None:
    with pytest.raises(SourceError, match=r"Hacker News \(front_page\)"):
        Algolia(answer).fetcher().fetch()


def write(tmp_path: Path, settings: dict[str, object]) -> Path:
    path = tmp_path / "lookout.yaml"
    path.write_text(
        yaml.safe_dump(
            {
                "database": str(tmp_path / "lookout.db"),
                "sources": [{"name": "hn", "type": "hackernews", **settings}],
            }
        )
    )
    return path


@pytest.mark.parametrize(
    ("settings", "message"),
    [
        ({"feed": "best"}, "'feed' must be one of front_page, newest, ask, show"),
        ({"min_points": -1}, "'min_points' must be a whole number"),
        ({"min_points": True}, "'min_points'"),
        ({"limit": 0}, "'limit' must be a whole number from 1 to 100"),
        ({"limit": 101}, "'limit'"),
        ({"limit": "many"}, "'limit'"),
    ],
)
def test_settings_are_validated(tmp_path: Path, settings: dict[str, object], message: str) -> None:
    with pytest.raises(ConfigError, match=message):
        build(load(write(tmp_path, settings), {}))


def test_a_configured_source_fills_the_inbox_end_to_end(tmp_path: Path) -> None:
    lookout = Lookout(
        tmp_path,
        sources=[{"name": "hn", "type": "hackernews", "min_points": 50, "limit": 5}],
    )
    lookout.network.hackernews = Algolia()
    lookout("run")
    inbox = lookout("inbox")
    assert "Rust 1.99 released" in inbox
    assert "how do you triage feeds" in inbox
    assert FEED_URL not in inbox
