"""GitHub over HTTPS with a token, for servers where no ``gh`` login exists."""

from typing import Any, cast

import httpx

from lookout.adapters.github.base import ApiGateway
from lookout.application.github import GitHubError

NOT_MODIFIED = 304
RATE_LIMITED = (403, 429)
USER_AGENT = "Lookout/0 (+https://github.com/bhoudebert/lookout)"


class RestGateway(ApiGateway):
    """Calls the REST API, with conditional requests so an unchanged answer costs no rate limit."""

    def __init__(self, client: httpx.Client, token: str, base_url: str = "https://api.github.com") -> None:
        self._client = client
        self._base = base_url.rstrip("/")
        self._headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": USER_AGENT,
        }
        self._cache: dict[str, tuple[str, object]] = {}

    @property
    def via(self) -> str:
        return "token"

    def _get(self, path: str) -> object:
        headers = dict(self._headers)
        cached = self._cache.get(path)
        if cached is not None:
            headers["If-None-Match"] = cached[0]
        try:
            response = self._client.get(f"{self._base}/{path}", headers=headers)
        except httpx.HTTPError as error:
            msg = f"{path}: {error}"
            raise GitHubError(msg) from error
        if response.status_code == NOT_MODIFIED and cached is not None:
            return cached[1]
        if response.status_code in RATE_LIMITED and response.headers.get("x-ratelimit-remaining") == "0":
            reset = response.headers.get("x-ratelimit-reset", "an unknown time")
            msg = f"GitHub rate limit reached, it resets at {reset}"
            raise GitHubError(msg)
        if not response.is_success:
            msg = f"{path}: {response.status_code} {_message(response)}"
            raise GitHubError(msg)
        payload: object = response.json()
        if (etag := response.headers.get("etag")) is not None:
            self._cache[path] = (etag, payload)
        return payload


def _message(response: httpx.Response) -> str:
    if not response.headers.get("content-type", "").startswith("application/json"):
        return "refused"
    return str(cast("dict[str, Any]", response.json()).get("message", "refused"))
