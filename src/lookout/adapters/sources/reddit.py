"""Reddit communities through their public feeds (openspec: source-ingestion).

Reddit lets an anonymous client make about one request a minute, but one address can name several communities
(``r/rust+java``) and returns up to 100 posts of all of them, so a source asks once however many it lists.
"""

import re
import time
from collections.abc import Callable

import httpx

from lookout.adapters.sources.rss import USER_AGENT, raws_from_feed
from lookout.application.ports_sources import SourceError
from lookout.domain.raw import RawItem

SORTS = ("hot", "new")
MAX_LIMIT = 100
TOO_MANY_REQUESTS = 429
MAX_WAIT = 90.0
DEFAULT_WAIT = 60.0
_NAME = re.compile(r"^[A-Za-z0-9_]{2,21}$")
_ADDRESS = re.compile(
    r"^(?:(?:https?://)?(?:www\.|old\.)?reddit\.com)?/?r/(?P<name>[^/?#\s]+)", re.IGNORECASE
)


def community(text: str) -> str:
    """The name of a community from what a person types: ``rust``, ``r/rust`` or its web address."""
    text = text.strip()
    found = _ADDRESS.match(text)
    return found.group("name") if found else text


def valid_community(name: str) -> bool:
    """Whether ``name`` can be a community's name."""
    return _NAME.match(name) is not None


class RedditFetcher:
    """The recent posts of several communities, in one request."""

    def __init__(
        self,
        name: str,
        communities: tuple[str, ...],
        client: httpx.Client,
        *,
        sort: str = "hot",
        limit: int = MAX_LIMIT,
        keywords: tuple[str, ...] = (),
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self._name = name
        self._communities = communities
        self._client = client
        self._sort = sort
        self._limit = limit
        self._keywords = tuple(k.lower() for k in keywords)
        self._sleep = sleep

    @property
    def name(self) -> str:
        return self._name

    @property
    def url(self) -> str:
        """The one address that serves every community of the source."""
        where = "" if self._sort == "hot" else f"{self._sort}/"
        return f"https://www.reddit.com/r/{'+'.join(self._communities)}/{where}.rss?limit={self._limit}"

    def fetch(self) -> tuple[RawItem, ...]:
        """The posts that pass the keyword filter. When Reddit says to slow down, wait once and try again."""
        response = self._get()
        if response.status_code == TOO_MANY_REQUESTS:
            self._sleep(_wait(response))
            response = self._get()
        if response.status_code == TOO_MANY_REQUESTS:
            msg = "Reddit is limiting requests from here; Lookout will try again later"
            raise SourceError(msg)
        try:
            response.raise_for_status()
        except httpx.HTTPError as error:
            msg = f"{self.url}: {error}"
            raise SourceError(msg) from error
        return raws_from_feed(self._name, self.url, response.content, self._keywords)

    def _get(self) -> httpx.Response:
        try:
            return self._client.get(self.url, headers={"User-Agent": USER_AGENT}, follow_redirects=True)
        except httpx.HTTPError as error:
            msg = f"{self.url}: {error}"
            raise SourceError(msg) from error


def _wait(response: httpx.Response) -> float:
    try:
        seconds = float(response.headers.get("x-ratelimit-reset", DEFAULT_WAIT))
    except ValueError:
        seconds = DEFAULT_WAIT
    return min(max(seconds, 1.0), MAX_WAIT) + 1.0
