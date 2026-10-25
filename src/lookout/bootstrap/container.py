"""Wiring: builds every adapter from the configuration and hands the use cases to the entry points."""

import re
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field, replace
from datetime import datetime
from pathlib import Path
from typing import cast

import httpx

from lookout.adapters.clock import SystemClock
from lookout.adapters.github.gh_cli import GhCliGateway, gh_is_logged_in
from lookout.adapters.github.rest import RestGateway
from lookout.adapters.github.unavailable import UnavailableGateway
from lookout.adapters.llm.openai_compatible import OpenAiEnricher
from lookout.adapters.sources.github import WATCHABLE as GITHUB_WATCHABLE
from lookout.adapters.sources.github import GitHubFetcher, repo_path
from lookout.adapters.sources.hackernews import FEEDS as HN_FEEDS
from lookout.adapters.sources.hackernews import MAX_LIMIT as HN_MAX_LIMIT
from lookout.adapters.sources.hackernews import HackerNewsFetcher
from lookout.adapters.sources.osv import OsvFetcher
from lookout.adapters.sources.reddit import MAX_LIMIT as REDDIT_MAX_LIMIT
from lookout.adapters.sources.reddit import SORTS as REDDIT_SORTS
from lookout.adapters.sources.reddit import RedditFetcher, community, valid_community
from lookout.adapters.sources.rss import RssFetcher
from lookout.adapters.sources.youtube import YouTubeFetcher, channel_ref
from lookout.adapters.store.codec import encode
from lookout.adapters.store.sqlite import (
    Database,
    SqliteChannelDefinitions,
    SqliteFlags,
    SqliteItemRepository,
    SqliteSignalRepository,
    SqliteSourceDefinitions,
    SqliteSourceStatusRepository,
    SqliteUsageRepository,
)
from lookout.application.enrich import Enrich
from lookout.application.errors import ConfigError
from lookout.application.expire import AgeLimited, Expire
from lookout.application.github import GitHubGateway
from lookout.application.ingest import Ingest
from lookout.application.personalize import Personalize
from lookout.application.ports import Clock, ItemRepository
from lookout.application.ports_sources import SourceFetcher, SourceStatusRepository
from lookout.application.reassess import Reassess
from lookout.application.refile import Refile
from lookout.application.registry import InvalidError, Registry
from lookout.application.runs import RunCoordinator, RunReport
from lookout.application.services import Services
from lookout.application.source_types import FieldInfo, SourceTypeInfo
from lookout.application.sources import SourceDirectory
from lookout.application.triage import Inbox, Triage
from lookout.bootstrap.config import Config, load_config
from lookout.bootstrap.demo import seed_demo
from lookout.bootstrap.doctor import run_checks
from lookout.domain.channel import UnknownChannelError
from lookout.domain.policy import PriorityPolicy
from lookout.domain.retention import Retention
from lookout.domain.source import SourceDef
from lookout.domain.stack import StackEntry

HTTP_TIMEOUT = 30.0
LLM_TIMEOUT = 300.0


@dataclass(frozen=True, slots=True)
class Ways:
    """What source adapters may need from the outside, chosen once at wiring."""

    http: httpx.Client
    github: GitHubGateway
    stack: tuple[StackEntry, ...]
    now: Callable[[], datetime]
    retention: Retention = field(default_factory=Retention)


def _rss(source: SourceDef, ways: Ways) -> SourceFetcher:
    url = source.settings.get("url")
    if not isinstance(url, str) or not url:
        msg = f"source '{source.name}' (rss) needs a 'url'"
        raise ConfigError(msg)
    if not url.startswith(("http://", "https://")):
        msg = f"source '{source.name}' (rss): 'url' must start with http:// or https://"
        raise ConfigError(msg)
    return RssFetcher(source.name, url, ways.http, keywords=source.keywords)


REPO = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")


def _github(source: SourceDef, ways: Ways) -> SourceFetcher:
    repos = source.settings.get("repos")
    if (
        not isinstance(repos, list)
        or not repos
        or not all(isinstance(r, str) for r in cast("list[object]", repos))
    ):
        msg = f"source '{source.name}' (github) needs 'repos': a list of owner/name"
        raise ConfigError(msg)
    names = tuple(dict.fromkeys(repo_path(r) for r in cast("list[str]", repos)))
    for repo in names:
        if not REPO.match(repo):
            msg = f"source '{source.name}' (github): '{repo}' is not of the form owner/name"
            raise ConfigError(msg)
    watch = source.settings.get("watch", ["releases", "advisories"])
    if (
        not isinstance(watch, list)
        or not watch
        or not set(cast("list[object]", watch)) <= set(GITHUB_WATCHABLE)
    ):
        msg = f"source '{source.name}' (github): 'watch' must be a list of {', '.join(GITHUB_WATCHABLE)}"
        raise ConfigError(msg)
    return GitHubFetcher(source.name, names, tuple(cast("list[str]", watch)), ways.github)


def _osv(source: SourceDef, ways: Ways) -> SourceFetcher:
    kev = source.settings.get("kev", True)
    days = source.settings.get("since_days", 30)
    if not isinstance(kev, bool):
        msg = f"source '{source.name}' (osv): 'kev' must be true or false"
        raise ConfigError(msg)
    if isinstance(days, bool) or not isinstance(days, int) or days < 1:
        msg = f"source '{source.name}' (osv): 'since_days' must be a whole number of at least 1"
        raise ConfigError(msg)
    return OsvFetcher(source.name, ways.stack, ways.http, ways.now, kev=kev, since_days=days)


def _hackernews(source: SourceDef, ways: Ways) -> SourceFetcher:
    feed = source.settings.get("feed", "front_page")
    points = source.settings.get("min_points", 0)
    limit = source.settings.get("limit", 30)
    if feed not in HN_FEEDS:
        msg = f"source '{source.name}' (hackernews): 'feed' must be one of {', '.join(HN_FEEDS)}"
        raise ConfigError(msg)
    if isinstance(points, bool) or not isinstance(points, int) or points < 0:
        msg = f"source '{source.name}' (hackernews): 'min_points' must be a whole number, 0 or more"
        raise ConfigError(msg)
    if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= HN_MAX_LIMIT:
        msg = f"source '{source.name}' (hackernews): 'limit' must be a whole number from 1 to {HN_MAX_LIMIT}"
        raise ConfigError(msg)
    return HackerNewsFetcher(
        source.name,
        ways.http,
        feed=cast("str", feed),
        min_points=points,
        limit=limit,
        keywords=source.keywords,
    )


def _max_age(source: SourceDef, ways: Ways) -> int:
    """How old an entry of this source may be, in days (0: no limit); every type has it (ADR 0016)."""
    days = source.settings.get("max_age_days", ways.retention.max_age_days)
    if isinstance(days, bool) or not isinstance(days, int) or days < 0:
        msg = f"source '{source.name}': 'max_age_days' must be a whole number of days, 0 for no limit"
        raise ConfigError(msg)
    return days


def _max_age_field(retention: Retention) -> FieldInfo:
    return FieldInfo(
        "max_age_days",
        "Ignore entries older than (days)",
        "number",
        default=retention.max_age_days,
        help="0 keeps everything; older entries are never stored",
    )


def _reddit(source: SourceDef, ways: Ways) -> SourceFetcher:
    raw = source.settings.get("subreddits")
    if not isinstance(raw, list) or not raw or not all(isinstance(r, str) for r in cast("list[object]", raw)):
        msg = f"source '{source.name}' (reddit) needs 'subreddits': a list of communities"
        raise ConfigError(msg)
    names = tuple(dict.fromkeys(community(r) for r in cast("list[str]", raw)))
    for name in names:
        if not valid_community(name):
            msg = f"source '{source.name}' (reddit): '{name}' is not the name of a community"
            raise ConfigError(msg)
    sort = source.settings.get("sort", "hot")
    limit = source.settings.get("limit", REDDIT_MAX_LIMIT)
    if sort not in REDDIT_SORTS:
        msg = f"source '{source.name}' (reddit): 'sort' must be one of {', '.join(REDDIT_SORTS)}"
        raise ConfigError(msg)
    if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= REDDIT_MAX_LIMIT:
        msg = f"source '{source.name}' (reddit): 'limit' must be a whole number from 1 to {REDDIT_MAX_LIMIT}"
        raise ConfigError(msg)
    return RedditFetcher(
        source.name, names, ways.http, sort=cast("str", sort), limit=limit, keywords=source.keywords
    )


def _youtube(source: SourceDef, ways: Ways) -> SourceFetcher:
    channel = source.settings.get("channel")
    ref = channel_ref(channel) if isinstance(channel, str) else None
    if ref is None:
        msg = (
            f"source '{source.name}' (youtube) needs a 'channel': its @handle, its address or its id (UC...)"
        )
        raise ConfigError(msg)
    return YouTubeFetcher(source.name, ref, ways.http, keywords=source.keywords)


@dataclass(frozen=True, slots=True)
class SourceTypeSpec:
    """A type of source: what a form shows for it, and how to build its fetcher from a definition."""

    info: SourceTypeInfo
    build: Callable[[SourceDef, Ways], SourceFetcher]


SOURCE_TYPES: dict[str, SourceTypeSpec] = {
    "rss": SourceTypeSpec(
        SourceTypeInfo(
            "rss",
            "RSS or Atom feed",
            "Blogs, news, GitHub releases (.../releases.atom), Reddit (.rss), YouTube channels.",
            (FieldInfo("url", "Feed address", "text", required=True, help="https://example.com/feed.xml"),),
        ),
        _rss,
    ),
    "github": SourceTypeSpec(
        SourceTypeInfo(
            "github",
            "GitHub repositories",
            "Releases, security advisories and Dependabot alerts, through your gh login or a token.",
            (
                FieldInfo(
                    "repos",
                    "Repositories",
                    "list",
                    required=True,
                    help="owner/name or the repository address, one per line",
                ),
                FieldInfo(
                    "watch",
                    "Watch",
                    "list",
                    default=["releases", "advisories"],
                    help="releases, advisories, dependabot (needs access to the repository)",
                ),
            ),
        ),
        _github,
    ),
    "reddit": SourceTypeSpec(
        SourceTypeInfo(
            "reddit",
            "Reddit communities",
            "Posts of several subreddits at once (no scores: Reddit does not share them anonymously). "
            "Keep your communities in one source: Reddit allows about one request a minute.",
            (
                FieldInfo(
                    "subreddits",
                    "Communities",
                    "list",
                    required=True,
                    help="rust, r/java or an address, one per line",
                ),
                FieldInfo("sort", "Order", "text", default="hot", help="hot or new"),
                FieldInfo("limit", "Posts per run (1 to 100)", "number", default=100),
            ),
        ),
        _reddit,
    ),
    "youtube": SourceTypeSpec(
        SourceTypeInfo(
            "youtube",
            "YouTube channel",
            "The recent videos of one channel.",
            (
                FieldInfo(
                    "channel",
                    "Channel",
                    "text",
                    required=True,
                    help="@handle, the channel's address, or its id (UC...)",
                ),
            ),
        ),
        _youtube,
    ),
    "hackernews": SourceTypeSpec(
        SourceTypeInfo(
            "hackernews",
            "Hacker News",
            "Stories of the front page, the newest, Ask HN or Show HN, with the points and comments.",
            (
                FieldInfo(
                    "feed",
                    "List",
                    "text",
                    default="front_page",
                    help="front_page, newest, ask or show",
                ),
                FieldInfo("min_points", "Minimum points", "number", default=0),
                FieldInfo("limit", "Stories per run (1 to 100)", "number", default=30),
            ),
        ),
        _hackernews,
    ),
    "osv": SourceTypeSpec(
        SourceTypeInfo(
            "osv",
            "OSV vulnerabilities",
            "Vulnerabilities of the packages in your stack, with CISA's known-exploited flag.",
            (
                FieldInfo("since_days", "Only the last (days)", "number", default=30),
                FieldInfo("kev", "Flag CISA known-exploited", "bool", default=True),
            ),
        ),
        _osv,
    ),
}


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
    expire: Expire
    refile: Refile
    personalize: Personalize
    sources: SourceDirectory
    registry: Registry
    ways: Ways
    http: httpx.Client
    github_via: str
    llm_http: httpx.Client
    runs: RunCoordinator = field(init=False)

    def __post_init__(self) -> None:
        self.runs = RunCoordinator(self._run, self.clock)

    def fetchers(self) -> tuple[SourceFetcher, ...]:
        """A fetcher for every enabled source as stored now (ADR 0013), without its old entries."""
        return tuple(
            AgeLimited(SOURCE_TYPES[s.type].build(s, self.ways), _max_age(s, self.ways), self.clock)
            for s in self.registry.enabled_sources()
        )

    def close(self) -> None:
        """Release the database and the HTTP clients."""
        self.http.close()
        self.llm_http.close()
        self.database.close()

    def services(self) -> Services:
        """The application as the entry points see it. Untouched items that are due expire first."""
        self.expire.run()
        return Services(
            items=self.items,
            triage=self.triage,
            inbox=self.inbox,
            reassess=self.reassess,
            refile=self.refile,
            personalize=self.personalize,
            sources=self.sources,
            registry=self.registry,
            source_types=tuple(
                replace(spec.info, fields=(*spec.info.fields, _max_age_field(self.config.retention)))
                for spec in SOURCE_TYPES.values()
            ),
            runs=self.runs,
            clock=self.clock,
            run=self._run,
            doctor=lambda: run_checks(
                self.config, self.database, self.llm_http, self.fetchers(), self.github_via
            ),
            seed_demo=lambda: seed_demo(
                self.items,
                self.clock.now(),
                PriorityPolicy(self.config.thresholds, self.config.retention.rules_window_days),
                self.config.stack,
                self.registry.channels(),
            ),
            export=lambda: (encode(item) for item in self.items.all()),
            schedule_minutes=self.config.schedule.interval_minutes,
            dashboard_dir=self.config.dashboard_dir,
            close=self.close,
        )

    def _run(self) -> RunReport:
        report = RunReport(self.ingest.run(self.fetchers()), self.enrich.run())
        self.personalize.rerank()
        self.expire.run()
        return report


def _validator(ways: Ways) -> Callable[[SourceDef], None]:
    """What a source must pass before it is stored: its type exists and builds a fetcher from its settings."""

    def validate(source: SourceDef) -> None:
        spec = SOURCE_TYPES.get(source.type)
        if spec is None:
            msg = (
                f"source '{source.name}' has type {source.type!r}; supported types: {', '.join(SOURCE_TYPES)}"
            )
            raise InvalidError(msg)
        try:
            spec.build(source, ways)
            _max_age(source, ways)
        except ConfigError as error:
            raise InvalidError(str(error)) from error

    return validate


def load(path: Path, environ: dict[str, str] | None = None) -> Config:
    """Read the configuration, knowing which source types exist."""
    return load_config(path, tuple(SOURCE_TYPES), environ)


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
        return _assemble(
            config,
            database,
            clock,
            Ways(http, gateway, config.stack.entries, clock.now, config.retention),
            llm_http,
        )
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
    policy = PriorityPolicy(config.thresholds, config.retention.rules_window_days)
    registry = Registry(
        SqliteSourceDefinitions(database),
        SqliteChannelDefinitions(database),
        SqliteFlags(database),
        _validator(ways),
        items,
    )
    try:
        registry.seed(config.sources, config.channels)
    except (UnknownChannelError, InvalidError) as error:
        raise ConfigError(str(error)) from error
    enricher = OpenAiEnricher(
        llm_http,
        base_url=config.llm.base_url,
        model=config.llm.model,
        api_key=config.llm.api_key,
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
        ingest=Ingest(
            items,
            statuses,
            clock,
            policy,
            config.stack,
            body_limit=config.body_limit,
            catalogue=registry.catalogue,
        ),
        enrich=Enrich(
            items,
            enricher,
            SqliteUsageRepository(database),
            clock,
            policy,
            daily_limit=config.llm.daily_limit,
            profile=personalize.profile,
            catalogue=registry.catalogue,
        ),
        triage=Triage(items, personalize, clock),
        inbox=Inbox(items, clock),
        reassess=Reassess(items, policy, config.stack, clock),
        expire=Expire(items, clock, config.retention),
        refile=Refile(items, registry.catalogue),
        personalize=personalize,
        sources=SourceDirectory(registry, statuses),
        registry=registry,
        ways=ways,
        http=ways.http,
        github_via=ways.github.via,
        llm_http=llm_http,
    )
