"""YouTube channels through their public feeds (openspec: source-ingestion)."""

import re

import httpx

from lookout.adapters.sources.rss import USER_AGENT, RssFetcher
from lookout.application.ports_sources import SourceError
from lookout.domain.raw import RawItem

FEED = "https://www.youtube.com/feeds/videos.xml?channel_id="
_ID = re.compile(r"^UC[A-Za-z0-9_-]{22}$")
_CHANNEL_URL = re.compile(r"(?:youtube\.com)?/channel/(?P<id>UC[A-Za-z0-9_-]{22})", re.IGNORECASE)
_HANDLE_URL = re.compile(r"(?:youtube\.com)?/@(?P<handle>[A-Za-z0-9_.-]+)", re.IGNORECASE)
_FEED_LINK = re.compile(
    r'<link rel="alternate" type="application/rss\+xml"[^>]*channel_id=(UC[A-Za-z0-9_-]{22})'
)


def channel_ref(text: str) -> tuple[str, str] | None:
    """What a person typed, as ``("id", UC...)`` or ``("handle", name)``; ``None`` when it is neither.

    Accepts a channel id, a channel address, an ``@handle`` or its address.
    """
    text = text.strip()
    if _ID.match(text):
        return "id", text
    if (found := _CHANNEL_URL.search(text)) is not None:
        return "id", found.group("id")
    if (found := _HANDLE_URL.search(text)) is not None:
        return "handle", found.group("handle")
    if re.fullmatch(r"@?[A-Za-z0-9_.-]{3,30}", text):
        return "handle", text.removeprefix("@")
    return None


class YouTubeFetcher:
    """The recent videos of one channel."""

    def __init__(
        self,
        name: str,
        channel: tuple[str, str],
        client: httpx.Client,
        *,
        keywords: tuple[str, ...] = (),
    ) -> None:
        self._name = name
        self._channel = channel
        self._client = client
        self._keywords = keywords

    @property
    def name(self) -> str:
        return self._name

    def fetch(self) -> tuple[RawItem, ...]:
        """The channel's current videos that pass the keyword filter."""
        feed = RssFetcher(self._name, f"{FEED}{self._channel_id()}", self._client, keywords=self._keywords)
        return feed.fetch()

    def _channel_id(self) -> str:
        kind, value = self._channel
        if kind == "id":
            return value
        page = f"https://www.youtube.com/@{value}"
        try:
            response = self._client.get(page, headers={"User-Agent": USER_AGENT}, follow_redirects=True)
            response.raise_for_status()
        except httpx.HTTPError as error:
            msg = f"YouTube channel @{value}: {error}"
            raise SourceError(msg) from error
        found = _FEED_LINK.search(response.text)
        if found is None:
            msg = f"YouTube channel @{value}: no such channel (check the name, or use its address)"
            raise SourceError(msg)
        return found.group(1)
