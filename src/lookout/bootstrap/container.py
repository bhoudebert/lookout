"""Wiring: builds every adapter from the configuration and hands the use cases to the entry points."""

import re
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import cast

import httpx

from lookout.adapters.clock import SystemClock
from lookout.adapters.github.gh_cli import GhCliGateway, gh_is_logged_in
from lookout.adapters.github.rest import RestGateway
from lookout.adapters.github.unavailable import UnavailableGateway
from lookout.adapters.llm.openai_compatible import OpenAiEnricher
from lookout.adapters.sources.github import KINDS as GITHUB_KINDS
from lookout.adapters.sources.github import GitHubFetcher
from lookout.adapters.sources.rss import RssFetcher
from lookout.adapters.store.codec import encode
from lookout.adapters.store.sqlite import (
    Database,
    SqliteItemRepository,
    SqliteSignalRepository,
    SqliteSourceStatusRepository,
    SqliteUsageRepository,
)
from lookout.application.enrich import Enrich
from lookout.application.errors import ConfigError
from lookout.application.github import GitHubGateway
from lookout.application.ingest import Ingest
from lookout.application.personalize import Personalize
from lookout.application.ports import Clock, ItemRepository
from lookout.application.ports_sources import SourceFetcher, SourceStatusRepository
from lookout.application.reassess import Reassess
from lookout.application.runs import RunCoordinator, RunReport
from lookout.application.services import Services
from lookout.application.sources import DeclaredSource, SourceDirectory
from lookout.application.triage import Inbox, Triage
from lookout.bootstrap.config import Config, SourceConfig, load_config
from lookout.bootstrap.demo import seed_demo
from lookout.bootstrap.doctor import run_checks
from lookout.domain.policy import PriorityPolicy

HTTP_TIMEOUT = 30.0
LLM_TIMEOUT = 300.0


@dataclass(frozen=True, slots=True)
class Ways:
    """What source adapters may need from the outside, chosen once at wiring."""

    http: httpx.Client
    github: GitHubGateway


def _rss(source: SourceConfig, ways: Ways) -> SourceFetcher:
    url = source.settings.get("url")
    if not isinstance(url, str) or not url:
        msg = f"source '{source.name}' (rss) needs a 'url'"
        raise ConfigError(msg)
    return RssFetcher(source.name, url, ways.http, keywords=source.keywords)


REPO = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")


def _github(source: SourceConfig, ways: Ways) -> SourceFetcher:
    repos = source.settings.get("repos")
    if (
        not isinstance(repos, list)
        or not repos
        or not all(isinstance(r, str) for r in cast("list[object]", repos))
    ):
        msg = f"source '{source.name}' (github) needs 'repos': a list of owner/name"
        raise ConfigError(msg)
    for repo in cast("list[str]", repos):
        if not REPO.match(repo):
            msg = f"source '{source.name}' (github): '{repo}' is not of the form owner/name"
            raise ConfigError(msg)
    kinds = source.settings.get("kinds", ["releases", "advisories"])
    if not isinstance(kinds, list) or not kinds or not set(cast("list[object]", kinds)) <= set(GITHUB_KINDS):
        msg = f"source '{source.name}' (github): 'kinds' must be a list of {', '.join(GITHUB_KINDS)}"
        raise ConfigError(msg)
    return GitHubFetcher(
        source.name, tuple(cast("list[str]", repos)), tuple(cast("list[str]", kinds)), ways.github
    )


SOURCE_KINDS: dict[str, Callable[[SourceConfig, Ways], SourceFetcher]] = {"rss": _rss, "github": _github}


def choose_gateway(
    via: str,
    client: httpx.Client,
    environ: Mapping[str, str],
    *,
    logged_in: Callable[[], bool] = gh_is_logged_in,
) -> GitHubGateway:
    """How to reach GitHub: ``gh`` when logged in, else a token, else a gateway that says why not."""
    token = environ.get("LOOKOUT_GITHUB_TOKEN") or environ.get("GITHUB_TOKEN") or ""
    if via in ("auto", "gh") and logged_in():
        return GhCliGateway()
    if via in ("auto", "token") and token:
        return RestGateway(client, token)
    return UnavailableGateway()


@dataclass
class Container:
    """The assembled application."""

    config: Config
    database: Database
    items: ItemRepository
    statuses: SourceStatusRepository
    clock: Clock
    ingest: Ingest
    enrich: Enrich
    triage: Triage
    inbox: Inbox
    reassess: Reassess
    personalize: Personalize
    sources: SourceDirectory
    fetchers: tuple[SourceFetcher, ...]
    http: httpx.Client
    github_via: str
    llm_http: httpx.Client
    runs: RunCoordinator = field(init=False)

    def __post_init__(self) -> None:
        self.runs = RunCoordinator(self._run, self.clock)

    def close(self) -> None:
        """Release the database and the HTTP clients."""
        self.http.close()
        self.llm_http.close()
        self.database.close()

    def services(self) -> Services:
        """The application as the entry points see it."""
        return Services(
            items=self.items,
            triage=self.triage,
            inbox=self.inbox,
            reassess=self.reassess,
            personalize=self.personalize,
            sources=self.sources,
            runs=self.runs,
            clock=self.clock,
            run=self._run,
            doctor=lambda: run_checks(
                self.config, self.database, self.llm_http, self.fetchers, self.github_via
            ),
            seed_demo=lambda: seed_demo(
                self.items, self.clock.now(), PriorityPolicy(self.config.thresholds), self.config.stack
            ),
            export=lambda: (encode(item) for item in self.items.all()),
            schedule_minutes=self.config.schedule.interval_minutes,
            dashboard_dir=self.config.dashboard_dir,
            close=self.close,
        )

    def _run(self) -> RunReport:
        report = RunReport(self.ingest.run(self.fetchers), self.enrich.run())
        self.personalize.rerank()
        return report


def load(path: Path, environ: dict[str, str] | None = None) -> Config:
    """Read the configuration, knowing which source kinds exist."""
    return load_config(path, tuple(SOURCE_KINDS), environ)


def build(
    config: Config,
    *,
    transport: httpx.BaseTransport | None = None,
    clock: Clock | None = None,
    github: GitHubGateway | None = None,
    environ: Mapping[str, str] | None = None,
) -> Container:
    """Wire adapters to use cases. ``transport`` lets tests answer every HTTP call."""
    clock = clock or SystemClock()
    config.database.parent.mkdir(parents=True, exist_ok=True)
    database = Database(config.database)
    http = httpx.Client(transport=transport, timeout=HTTP_TIMEOUT)
    llm_http = httpx.Client(transport=transport, timeout=LLM_TIMEOUT)
    try:
        gateway = github or choose_gateway(config.github.via, http, environ or {})
        return _assemble(config, database, clock, Ways(http, gateway), llm_http)
    except Exception:
        http.close()
        llm_http.close()
        database.close()
        raise


def _assemble(
    config: Config, database: Database, clock: Clock, ways: Ways, llm_http: httpx.Client
) -> Container:
    items = SqliteItemRepository(database)
    statuses = SqliteSourceStatusRepository(database)
    personalize = Personalize(
        items,
        SqliteSignalRepository(database),
        clock,
        half_life_days=config.personalization.half_life_days,
        minimum_signals=config.personalization.minimum_signals,
    )
    policy = PriorityPolicy(config.thresholds)
    enricher = OpenAiEnricher(
        llm_http,
        base_url=config.llm.base_url,
        model=config.llm.model,
        api_key=config.llm.api_key,
        categories=config.categories,
        interests=config.interests,
        stack=tuple(e.name for e in config.stack.entries),
        summary_chars=config.llm.summary_chars,
    )
    return Container(
        config=config,
        database=database,
        items=items,
        statuses=statuses,
        clock=clock,
        ingest=Ingest(items, statuses, clock, policy, config.stack, body_limit=config.body_limit),
        enrich=Enrich(
            items,
            enricher,
            SqliteUsageRepository(database),
            clock,
            policy,
            daily_limit=config.llm.daily_limit,
            profile=personalize.profile,
        ),
        triage=Triage(items, personalize),
        inbox=Inbox(items, clock),
        reassess=Reassess(items, policy, config.stack),
        personalize=personalize,
        sources=SourceDirectory(
            tuple(DeclaredSource(s.name, s.kind, s.enabled) for s in config.sources), statuses
        ),
        fetchers=tuple(SOURCE_KINDS[s.kind](s, ways) for s in config.sources if s.enabled),
        http=ways.http,
        github_via=ways.github.via,
        llm_http=llm_http,
    )
