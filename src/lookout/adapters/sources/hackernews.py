"""Hacker News stories through its public search API (openspec: source-ingestion)."""

from datetime import UTC, datetime
from typing import Any, cast

import httpx

from lookout.adapters.sources.rss import USER_AGENT
from lookout.application.ports_sources import SourceError
from lookout.domain.keywords import wanted
from lookout.domain.raw import RawItem

API = "https://hn.algolia.com/api/v1"
DISCUSSION = "https://news.ycombinator.com/item?id="
MAX_LIMIT = 100

# feed name -> (endpoint, tag asked for, tag the item carries)
FEEDS: dict[str, tuple[str, str, str]] = {
    "front_page": ("search", "front_page", ""),
    "newest": ("search_by_date", "story", ""),
    "ask": ("search_by_date", "ask_hn", "ask-hn"),
    "show": ("search_by_date", "show_hn", "show-hn"),
}


class HackerNewsFetcher:
    """One list of Hacker News stories, optionally only those with enough points."""

    def __init__(
        self,
        name: str,
        client: httpx.Client,
        *,
        feed: str = "front_page",
        min_points: int = 0,
        limit: int = 30,
        keywords: tuple[str, ...] = (),
    ) -> None:
        self._name = name
        self._client = client
        self._feed = feed
        self._min_points = min_points
        self._limit = limit
        self._keywords = keywords

    @property
    def name(self) -> str:
        return self._name

    def fetch(self) -> tuple[RawItem, ...]:
        """The current stories of the chosen list that pass the points and keyword filters."""
        endpoint, tag, label = FEEDS[self._feed]
        params: dict[str, str | int] = {"tags": tag, "hitsPerPage": self._limit}
        if self._min_points > 0:
            params["numericFilters"] = f"points>={self._min_points}"
        try:
            response = self._client.get(
                f"{API}/{endpoint}", params=params, headers={"User-Agent": USER_AGENT}
            )
            response.raise_for_status()
            hits = cast("list[dict[str, Any]]", response.json()["hits"])
        except (httpx.HTTPError, ValueError, KeyError, TypeError) as error:
            msg = f"Hacker News ({self._feed}): {error}"
            raise SourceError(msg) from error
        raws = (self._raw(hit, label) for hit in hits if hit.get("title") and hit.get("objectID"))
        return tuple(r for r in raws if wanted(r, self._keywords))

    def _raw(self, hit: dict[str, Any], label: str) -> RawItem:
        discussion = f"{DISCUSSION}{hit['objectID']}"
        points, comments = int(hit.get("points") or 0), int(hit.get("num_comments") or 0)
        facts = f"{points} points and {comments} comments on Hacker News: {discussion}"
        text = str(hit.get("story_text") or "")
        created = hit.get("created_at_i")
        return RawItem(
            source=self._name,
            url=str(hit.get("url") or discussion),
            title=str(hit["title"]),
            body=f"{text}\n\n{facts}" if text else facts,
            published_at=datetime.fromtimestamp(created, UTC) if isinstance(created, int) else None,
            author=str(hit.get("author") or ""),
            tags=(label,) if label else (),
        )
