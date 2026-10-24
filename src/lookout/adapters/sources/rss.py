"""RSS and Atom feeds (openspec: source-ingestion)."""

from calendar import timegm
from datetime import UTC, datetime
from typing import Any, cast

import httpx

from lookout.adapters.sources._feed import parse_feed
from lookout.application.ports_sources import SourceError
from lookout.domain.raw import RawItem

USER_AGENT = "Lookout/0 (+https://github.com/bhoudebert/lookout)"


class RssFetcher:
    """Reads one feed. Network and parsing problems become ``SourceError`` with a readable message."""

    def __init__(
        self,
        name: str,
        url: str,
        client: httpx.Client,
        *,
        keywords: tuple[str, ...] = (),
    ) -> None:
        self._name = name
        self._url = url
        self._client = client
        self._keywords = tuple(k.lower() for k in keywords)

    @property
    def name(self) -> str:
        return self._name

    def fetch(self) -> tuple[RawItem, ...]:
        """The feed's current entries that pass the keyword filter."""
        try:
            response = self._client.get(self._url, headers={"User-Agent": USER_AGENT}, follow_redirects=True)
            response.raise_for_status()
        except httpx.HTTPError as error:
            msg = f"{self._url}: {error}"
            raise SourceError(msg) from error
        parsed = parse_feed(response.content)
        if parsed.problem is not None:
            msg = f"{self._url}: not a readable feed ({parsed.problem})"
            raise SourceError(msg)
        raws = (self._raw(entry) for entry in parsed.entries if entry.get("link"))
        return tuple(r for r in raws if self._wanted(r))

    def _raw(self, entry: dict[str, Any]) -> RawItem:
        link = str(entry["link"])
        contents = cast("list[dict[str, Any]]", entry.get("content") or [{}])
        body = contents[0].get("value") or entry.get("summary") or ""
        return RawItem(
            source=self._name,
            url=link,
            title=str(entry.get("title") or link),
            body=str(body),
            published_at=_moment(entry.get("published_parsed") or entry.get("updated_parsed")),
        )

    def _wanted(self, raw: RawItem) -> bool:
        if not self._keywords:
            return True
        text = f"{raw.title}\n{raw.body}".lower()
        return any(k in text for k in self._keywords)


def _moment(parsed: Any) -> datetime | None:  # noqa: ANN401
    return datetime.fromtimestamp(timegm(parsed), tz=UTC) if parsed else None
