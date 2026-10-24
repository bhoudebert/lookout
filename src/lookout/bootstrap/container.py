"""Wiring: builds every adapter from the configuration and hands the use cases to the entry points."""

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

import httpx

from lookout.adapters.clock import SystemClock
from lookout.adapters.llm.openai_compatible import OpenAiEnricher
from lookout.adapters.sources.rss import RssFetcher
from lookout.adapters.store.sqlite import (
    Database,
    SqliteItemRepository,
    SqliteSourceStatusRepository,
    SqliteUsageRepository,
)
from lookout.application.enrich import Enrich
from lookout.application.errors import ConfigError
from lookout.application.ingest import Ingest
from lookout.application.ports import Clock, ItemRepository
from lookout.application.ports_sources import SourceFetcher, SourceStatusRepository
from lookout.application.reassess import Reassess
from lookout.application.services import RunReport, Services
from lookout.application.triage import Inbox, Triage
from lookout.bootstrap.config import Config, SourceConfig, load_config
from lookout.bootstrap.demo import seed_demo
from lookout.bootstrap.doctor import run_checks
from lookout.domain.policy import PriorityPolicy

HTTP_TIMEOUT = 30.0
LLM_TIMEOUT = 300.0


def _rss(source: SourceConfig, client: httpx.Client) -> SourceFetcher:
    url = source.settings.get("url")
    if not isinstance(url, str) or not url:
        msg = f"source '{source.name}' (rss) needs a 'url'"
        raise ConfigError(msg)
    return RssFetcher(source.name, url, client, keywords=source.keywords)


SOURCE_KINDS: dict[str, Callable[[SourceConfig, httpx.Client], SourceFetcher]] = {"rss": _rss}


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
    fetchers: tuple[SourceFetcher, ...]
    http: httpx.Client
    llm_http: httpx.Client

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
            clock=self.clock,
            run=self._run,
            doctor=lambda: run_checks(self.config, self.database, self.llm_http, self.fetchers),
            seed_demo=lambda: seed_demo(
                self.items, self.clock.now(), PriorityPolicy(self.config.thresholds), self.config.stack
            ),
            close=self.close,
        )

    def _run(self) -> RunReport:
        return RunReport(self.ingest.run(self.fetchers), self.enrich.run())


def load(path: Path, environ: dict[str, str] | None = None) -> Config:
    """Read the configuration, knowing which source kinds exist."""
    return load_config(path, tuple(SOURCE_KINDS), environ)


def build(
    config: Config,
    *,
    transport: httpx.BaseTransport | None = None,
    clock: Clock | None = None,
) -> Container:
    """Wire adapters to use cases. ``transport`` lets tests answer every HTTP call."""
    clock = clock or SystemClock()
    config.database.parent.mkdir(parents=True, exist_ok=True)
    database = Database(config.database)
    http = httpx.Client(transport=transport, timeout=HTTP_TIMEOUT)
    llm_http = httpx.Client(transport=transport, timeout=LLM_TIMEOUT)
    try:
        return _assemble(config, database, clock, http, llm_http)
    except Exception:
        http.close()
        llm_http.close()
        database.close()
        raise


def _assemble(
    config: Config, database: Database, clock: Clock, http: httpx.Client, llm_http: httpx.Client
) -> Container:
    items = SqliteItemRepository(database)
    statuses = SqliteSourceStatusRepository(database)
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
        ),
        triage=Triage(items),
        inbox=Inbox(items, clock),
        reassess=Reassess(items, policy, config.stack),
        fetchers=tuple(SOURCE_KINDS[s.kind](s, http) for s in config.sources if s.enabled),
        http=http,
        llm_http=llm_http,
    )
