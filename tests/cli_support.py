"""A whole Lookout on fakes: real wiring, real SQLite, scripted network."""

import json
from pathlib import Path
from typing import TYPE_CHECKING, Any

import httpx
import yaml
from fastapi import FastAPI
from fastapi.testclient import TestClient
from tests.github_support import FakeGitHub
from tests.support import FixedClock

if TYPE_CHECKING:
    from collections.abc import Callable

from typer.testing import CliRunner

from lookout.adapters.cli.app import create_app
from lookout.application.github import GitHubGateway
from lookout.application.services import Services
from lookout.bootstrap.container import build, load

FIXTURES = Path(__file__).parent / "fixtures"
FEED_URL = "https://example.com/feed"
LLM_URL = "http://localhost:11434/v1"
runner = CliRunner()


def reading(**overrides: Any) -> str:
    answer = {
        "summary": "A summary.",
        "tags": ["python"],
        "score": 75,
        "action_needed": False,
        "reason": "relevant",
    }
    return json.dumps({**answer, **overrides})


def _stream(content: str) -> bytes:
    """The answer as a model server streams it: a few pieces, then the reason it stopped."""
    cut = max(1, len(content) // 3)
    pieces = [content[i : i + cut] for i in range(0, len(content), cut)] or [""]
    events: list[dict[str, Any]] = [
        {"choices": [{"delta": {"content": p}, "finish_reason": None}]} for p in pieces
    ]
    events.append({"choices": [{"delta": {}, "finish_reason": "stop"}]})
    return ("".join(f"data: {json.dumps(e)}\n\n" for e in events) + "data: [DONE]\n\n").encode()


class Network:
    """Answers the feed, the model list and the chat endpoint; each can be switched to fail."""

    def __init__(self) -> None:
        self.feed: bytes | int = (FIXTURES / "feed.rss").read_bytes()
        self.models: object = {"data": [{"id": "llama3.1"}]}
        self.chat: Callable[[httpx.Request], str] = lambda _request: reading()
        self.llm_down = False
        self.requests: list[httpx.Request] = []
        self.osv: Callable[[httpx.Request], httpx.Response] = lambda _request: httpx.Response(
            200, json={"vulns": []}
        )
        self.kev: bytes | int = json.dumps({"vulnerabilities": []}).encode()
        self.reddit: Callable[[httpx.Request], httpx.Response] = lambda _request: httpx.Response(404)
        self.youtube: Callable[[httpx.Request], httpx.Response] = lambda _request: httpx.Response(404)
        self.hackernews: Callable[[httpx.Request], httpx.Response] = lambda _request: httpx.Response(
            200, json={"hits": []}
        )

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        url = str(request.url)
        if url.startswith(LLM_URL):
            return self._model(request, url)
        scripted = {
            "https://api.osv.dev/v1/query": self.osv,
            "https://www.reddit.com/": self.reddit,
            "https://www.youtube.com/": self.youtube,
            "https://hn.algolia.com/": self.hackernews,
        }
        for prefix, answer in scripted.items():
            if url.startswith(prefix):
                return answer(request)
        if url.startswith("https://www.cisa.gov/"):
            return self._served(self.kev)
        return self._served(self.feed) if url == FEED_URL else httpx.Response(404)

    def _model(self, request: httpx.Request, url: str) -> httpx.Response:
        if self.llm_down:
            raise httpx.ConnectError("connection refused", request=request)
        if url.endswith("/models"):
            return httpx.Response(200, json=self.models)
        content = self.chat(request)
        if json.loads(request.content).get("stream"):
            return httpx.Response(
                200, content=_stream(content), headers={"Content-Type": "text/event-stream"}
            )
        return httpx.Response(200, json={"choices": [{"message": {"content": content}}]})

    @staticmethod
    def _served(content: bytes | int) -> httpx.Response:
        return httpx.Response(content) if isinstance(content, int) else httpx.Response(200, content=content)


class Lookout:
    """A configured instance in a temporary directory, driven through the command line."""

    def __init__(self, tmp_path: Path, github: GitHubGateway | None = None, **config: Any) -> None:
        self.github = github or FakeGitHub()
        self.network = Network()
        self.clock = FixedClock()
        self.path = tmp_path / "lookout.yaml"
        self.config: dict[str, Any] = {
            "database": str(tmp_path / "lookout.db"),
            "stack": [{"name": "django", "ecosystem": "pypi"}],
            "sources": [{"name": "blog", "type": "rss", "url": FEED_URL}],
            **config,
        }
        self.write()
        self.served: list[tuple[str, int]] = []
        self.app = create_app(self._open, self._serve)

    def services(self) -> Services:
        return self._open(self.path)

    def _serve(self, services: Services, host: str, port: int) -> None:
        self.served.append((host, port))
        assert services.items is not None

    def write(self) -> None:
        self.path.write_text(yaml.safe_dump(self.config))

    def _open(self, path: Path) -> Services:
        container = build(
            load(path, {}), transport=httpx.MockTransport(self.network), clock=self.clock, github=self.github
        )
        return container.services()

    def __call__(self, *args: str, exit_code: int = 0) -> str:
        result = runner.invoke(self.app, ["--config", str(self.path), *args])
        assert result.exit_code == exit_code, result.output
        return result.output


def http_client(api: FastAPI) -> httpx.Client:
    """A test client typed as the plain httpx client it is."""
    return TestClient(api)
