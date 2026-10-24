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
        "kind": "release",
        "tags": ["python"],
        "score": 75,
        "action_needed": False,
        "reason": "relevant",
    }
    return json.dumps({**answer, **overrides})


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

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        url = str(request.url)
        if url.startswith(LLM_URL):
            return self._model(request, url)
        if url == "https://api.osv.dev/v1/query":
            return self.osv(request)
        if url.startswith("https://www.cisa.gov/"):
            return self._served(self.kev)
        if url == FEED_URL:
            return self._served(self.feed)
        return httpx.Response(404)

    def _model(self, request: httpx.Request, url: str) -> httpx.Response:
        if self.llm_down:
            raise httpx.ConnectError("connection refused", request=request)
        if url.endswith("/models"):
            return httpx.Response(200, json=self.models)
        content = self.chat(request)
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
