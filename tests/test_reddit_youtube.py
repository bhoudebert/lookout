"""Scenarios of openspec/specs/source-ingestion: Reddit communities and YouTube channels."""

from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import httpx
import pytest
import yaml
from tests.cli_support import Lookout, reading
from tests.support import NOW

from lookout.adapters.sources.reddit import RedditFetcher, community, valid_community
from lookout.adapters.sources.youtube import FEED, YouTubeFetcher, channel_ref
from lookout.application.errors import ConfigError
from lookout.application.ports_sources import SourceError
from lookout.bootstrap.container import build, load


def stamp(**ago: float) -> str:
    return (NOW - timedelta(**ago)).strftime("%Y-%m-%dT%H:%M:%S+00:00")


REDDIT = f"""<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom"><title>multi</title>
<entry><author><name>/u/ferris</name></author><category term="rust" label="r/rust"/>
<content type="html">&lt;p&gt;async closures landed&lt;/p&gt;</content>
<link href="https://www.reddit.com/r/rust/comments/1/async_closures/"/>
<updated>{stamp(hours=2)}</updated><title>Async closures are stable</title></entry>
<entry><author><name>/u/duke</name></author><category term="java" label="r/java"/>
<link href="https://www.reddit.com/r/java/comments/2/loom/"/>
<updated>{stamp(hours=3)}</updated><title>Virtual threads in production</title></entry>
<entry><title>No link, skipped</title></entry>
</feed>"""

YT_FEED = f"""<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns:yt="http://www.youtube.com/xml/schemas/2015" xmlns="http://www.w3.org/2005/Atom">
<title>Fireship</title>
<entry><title>Rust in 100 seconds</title><link rel="alternate" href="https://www.youtube.com/watch?v=abc123"/>
<author><name>Fireship</name></author><published>{stamp(hours=5)}</published></entry>
</feed>"""

ID = "UCsBjURrPoezykLs9EqgamOA"
PAGE = f'<html><head><link rel="alternate" type="application/rss+xml" href="{FEED}{ID}"></head></html>'


class Web:
    """Reddit and YouTube, scripted; remembers what was asked."""

    def __init__(self, *answers: httpx.Response) -> None:
        self.answers = list(answers)
        self.requests: list[httpx.Request] = []

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        return self.answers.pop(0) if len(self.answers) > 1 else self.answers[0]

    @property
    def client(self) -> httpx.Client:
        return httpx.Client(transport=httpx.MockTransport(self))


def reddit(web: Web, *communities: str, **kw: Any) -> RedditFetcher:
    slept: list[float] = kw.pop("slept", [])
    return RedditFetcher("r", communities or ("rust", "java"), web.client, sleep=slept.append, **kw)


# --- Reddit ---


def test_one_request_serves_every_community_and_each_post_is_an_item() -> None:
    web = Web(httpx.Response(200, content=REDDIT.encode()))
    first, second = reddit(web).fetch()
    assert [str(r.url) for r in web.requests] == ["https://www.reddit.com/r/rust+java/.rss?limit=100"]
    assert (first.url, first.title, first.author) == (
        "https://www.reddit.com/r/rust/comments/1/async_closures/",
        "Async closures are stable",
        "/u/ferris",
    )
    assert first.tags == ("rust",)
    assert second.tags == ("java",)
    assert "async closures landed" in first.body


@pytest.mark.parametrize(
    ("kw", "url"),
    [
        ({"sort": "new", "limit": 10}, "https://www.reddit.com/r/rust+java/new/.rss?limit=10"),
        ({"sort": "hot"}, "https://www.reddit.com/r/rust+java/.rss?limit=100"),
    ],
)
def test_the_order_and_the_number_of_posts_are_asked_of_reddit(kw: dict[str, Any], url: str) -> None:
    web = Web(httpx.Response(200, content=REDDIT.encode()))
    fetcher = reddit(web, **kw)
    fetcher.fetch()
    assert fetcher.url == url == str(web.requests[0].url)


def test_keywords_keep_only_matching_posts() -> None:
    web = Web(httpx.Response(200, content=REDDIT.encode()))
    assert [r.title for r in reddit(web, keywords=("LOOM", "virtual")).fetch()] == [
        "Virtual threads in production"
    ]
    assert reddit(web).name == "r"


def test_when_reddit_says_slow_down_the_source_waits_as_told_and_tries_once_more() -> None:
    web = Web(
        httpx.Response(429, headers={"x-ratelimit-reset": "47"}), httpx.Response(200, content=REDDIT.encode())
    )
    slept: list[float] = []
    assert len(reddit(web, slept=slept).fetch()) == 2
    assert slept == [48.0]
    assert len(web.requests) == 2


@pytest.mark.parametrize(
    ("header", "waited"),
    [
        ({}, 61.0),
        ({"x-ratelimit-reset": "soon"}, 61.0),
        ({"x-ratelimit-reset": "900"}, 91.0),
        ({"x-ratelimit-reset": "0"}, 2.0),
    ],
)
def test_the_wait_is_bounded_and_has_a_default(header: dict[str, str], waited: float) -> None:
    web = Web(httpx.Response(429, headers=header), httpx.Response(200, content=REDDIT.encode()))
    slept: list[float] = []
    reddit(web, slept=slept).fetch()
    assert slept == [waited]


def test_a_source_reddit_keeps_refusing_fails_with_a_message_that_says_it_will_retry() -> None:
    web = Web(httpx.Response(429))
    with pytest.raises(SourceError, match="Lookout will try again later"):
        reddit(web).fetch()
    assert len(web.requests) == 2


@pytest.mark.parametrize(
    "answer",
    [httpx.Response(500), httpx.Response(200, content=b"<html>nope</html>")],
)
def test_other_failures_name_the_address(answer: httpx.Response) -> None:
    with pytest.raises(SourceError, match=r"reddit\.com/r/rust\+java"):
        reddit(Web(answer)).fetch()


def test_a_network_failure_is_a_source_error() -> None:
    def down(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("no route", request=request)

    fetcher = RedditFetcher(
        "r", ("rust",), httpx.Client(transport=httpx.MockTransport(down)), sleep=lambda _s: None
    )
    with pytest.raises(SourceError, match="no route"):
        fetcher.fetch()


@pytest.mark.parametrize(
    ("typed", "name"),
    [
        ("rust", "rust"),
        (" r/rust ", "rust"),
        ("/r/rust/", "rust"),
        ("https://www.reddit.com/r/rust/comments/1/x", "rust"),
        ("old.reddit.com/r/java", "java"),
        ("LocalLLaMA", "LocalLLaMA"),
    ],
)
def test_a_community_may_be_written_as_a_name_or_an_address(typed: str, name: str) -> None:
    assert community(typed) == name
    assert valid_community(name)


@pytest.mark.parametrize("bad", ["", "a", "two words", "r/", "https://example.com/r", "x" * 22])
def test_what_is_not_a_community_name_is_refused(bad: str) -> None:
    assert not valid_community(community(bad))


# --- YouTube ---


@pytest.mark.parametrize(
    ("typed", "ref"),
    [
        (ID, ("id", ID)),
        (f"https://www.youtube.com/channel/{ID}", ("id", ID)),
        (f"youtube.com/channel/{ID}/videos", ("id", ID)),
        ("@fireship", ("handle", "fireship")),
        ("fireship", ("handle", "fireship")),
        ("https://www.youtube.com/@fireship", ("handle", "fireship")),
        ("https://www.youtube.com/@fireship/videos", ("handle", "fireship")),
        ("  @Fire.ship  ", ("handle", "Fire.ship")),
    ],
)
def test_a_channel_may_be_written_as_a_handle_an_address_or_an_id(typed: str, ref: tuple[str, str]) -> None:
    assert channel_ref(typed) == ref


@pytest.mark.parametrize("bad", ["", "ab", "two words", "https://example.com/x y", "UC-too-short y"])
def test_what_is_not_a_channel_is_refused(bad: str) -> None:
    assert channel_ref(bad) is None


def youtube(web: Web, channel: tuple[str, str], **kw: Any) -> YouTubeFetcher:
    return YouTubeFetcher("yt", channel, web.client, **kw)


def test_a_handle_is_resolved_through_the_channel_page_and_its_videos_become_items() -> None:
    web = Web(httpx.Response(200, text=PAGE), httpx.Response(200, content=YT_FEED.encode()))
    [video] = youtube(web, ("handle", "fireship")).fetch()
    assert [str(r.url) for r in web.requests] == ["https://www.youtube.com/@fireship", f"{FEED}{ID}"]
    assert (video.url, video.title, video.author) == (
        "https://www.youtube.com/watch?v=abc123",
        "Rust in 100 seconds",
        "Fireship",
    )
    assert video.published_at == datetime.fromtimestamp((NOW - timedelta(hours=5)).timestamp(), UTC)
    assert youtube(web, ("id", ID)).name == "yt"


def test_an_id_needs_no_page_and_keywords_filter_the_videos() -> None:
    web = Web(httpx.Response(200, content=YT_FEED.encode()))
    assert len(youtube(web, ("id", ID)).fetch()) == 1
    assert [str(r.url) for r in web.requests] == [f"{FEED}{ID}"]
    web = Web(httpx.Response(200, content=YT_FEED.encode()))
    assert youtube(web, ("id", ID), keywords=("python",)).fetch() == ()


def test_a_handle_that_is_not_a_channel_says_so() -> None:
    web = Web(httpx.Response(200, text="<html>nothing here</html>"))
    with pytest.raises(SourceError, match="no such channel"):
        youtube(web, ("handle", "nobody")).fetch()


@pytest.mark.parametrize("answer", [httpx.Response(404), httpx.Response(503)])
def test_a_channel_page_that_fails_names_the_channel(answer: httpx.Response) -> None:
    with pytest.raises(SourceError, match="YouTube channel @nobody"):
        youtube(Web(answer), ("handle", "nobody")).fetch()


# --- configuration and the whole application ---


def write(tmp_path: Path, **source: object) -> Path:
    path = tmp_path / "lookout.yaml"
    path.write_text(yaml.safe_dump({"database": str(tmp_path / "db"), "sources": [{"name": "s", **source}]}))
    return path


@pytest.mark.parametrize(
    ("source", "message"),
    [
        ({"type": "reddit"}, "needs 'subreddits'"),
        ({"type": "reddit", "subreddits": []}, "needs 'subreddits'"),
        ({"type": "reddit", "subreddits": "rust"}, "needs 'subreddits'"),
        ({"type": "reddit", "subreddits": [1]}, "needs 'subreddits'"),
        ({"type": "reddit", "subreddits": ["two words"]}, "'two words' is not the name of a community"),
        ({"type": "reddit", "subreddits": ["rust"], "sort": "top"}, "'sort' must be one of hot, new"),
        (
            {"type": "reddit", "subreddits": ["rust"], "limit": 0},
            "'limit' must be a whole number from 1 to 100",
        ),
        ({"type": "reddit", "subreddits": ["rust"], "limit": True}, "'limit'"),
        ({"type": "youtube"}, "needs a 'channel'"),
        ({"type": "youtube", "channel": 7}, "needs a 'channel'"),
        ({"type": "youtube", "channel": "two words"}, "needs a 'channel'"),
    ],
)
def test_settings_are_validated(tmp_path: Path, source: dict[str, object], message: str) -> None:
    with pytest.raises(ConfigError, match=message):
        build(load(write(tmp_path, **source), {}))


def test_reddit_and_youtube_sources_fill_the_inbox(tmp_path: Path) -> None:
    lookout = Lookout(
        tmp_path,
        sources=[
            {
                "name": "reddit",
                "type": "reddit",
                "subreddits": ["r/rust", "rust", "https://reddit.com/r/java"],
            },
            {"name": "fireship", "type": "youtube", "channel": "@fireship"},
        ],
    )
    asked: list[str] = []

    def web(request: httpx.Request) -> httpx.Response:
        asked.append(str(request.url))
        url = str(request.url)
        if url.startswith("https://www.reddit.com/"):
            return httpx.Response(200, content=REDDIT.encode())
        if url.endswith("/@fireship"):
            return httpx.Response(200, text=PAGE)
        return httpx.Response(200, content=YT_FEED.encode())

    lookout.network.reddit = web
    lookout.network.youtube = web
    lookout.network.chat = lambda _request: reading()
    lookout("run")
    inbox = lookout("inbox")
    assert "Async closures are stable" in inbox
    assert "Rust in 100 seconds" in inbox
    assert asked.count("https://www.reddit.com/r/rust+java/.rss?limit=100") == 1
