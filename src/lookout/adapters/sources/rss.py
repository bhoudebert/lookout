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
        return raws_from_feed(self._name, self._url, response.content, self._keywords)


def raws_from_feed(name: str, url: str, content: bytes, keywords: tuple[str, ...]) -> tuple[RawItem, ...]:
    """The entries of feed bytes that pass the keyword filter; ``url`` only names the feed in a failure."""
    parsed = parse_feed(content)
    if parsed.problem is not None:
        msg = f"{url}: not a readable feed ({parsed.problem})"
        raise SourceError(msg)
    raws = (_raw(name, entry) for entry in parsed.entries if entry.get("link"))
    return tuple(r for r in raws if _wanted(r, keywords))


def _raw(source: str, entry: dict[str, Any]) -> RawItem:
    link = str(entry["link"])
    contents = cast("list[dict[str, Any]]", entry.get("content") or [{}])
    body = contents[0].get("value") or entry.get("summary") or ""
    return RawItem(
        source=source,
        url=link,
        title=str(entry.get("title") or link),
        body=str(body),
        published_at=_moment(entry.get("published_parsed") or entry.get("updated_parsed")),
        author=_author(entry),
        tags=_tags(entry),
    )


def _wanted(raw: RawItem, keywords: tuple[str, ...]) -> bool:
    if not keywords:
        return True
    text = f"{raw.title}\n{raw.body}".lower()
    return any(k in text for k in keywords)


def _author(entry: dict[str, Any]) -> str:
    name = entry.get("author")
    if isinstance(name, str) and name.strip():
        return name.strip()
    authors = entry.get("authors")
    first = cast("list[object]", authors)[0] if isinstance(authors, list) and authors else None
    found = cast("dict[str, Any]", first).get("name") if isinstance(first, dict) else None
    return found.strip() if isinstance(found, str) else ""


def _tags(entry: dict[str, Any]) -> tuple[str, ...]:
    raw = entry.get("tags")
    terms = (
        (cast("dict[str, Any]", t).get("term") for t in cast("list[object]", raw) if isinstance(t, dict))
        if isinstance(raw, list)
        else ()
    )
    return tuple(t.strip() for t in terms if isinstance(t, str) and t.strip())


def _moment(parsed: Any) -> datetime | None:  # noqa: ANN401
    return datetime.fromtimestamp(timegm(parsed), tz=UTC) if parsed else None
