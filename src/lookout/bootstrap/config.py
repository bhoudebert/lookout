"""Reading ``lookout.yaml`` (openspec: cli). Errors name the file, the key and the expected form."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, cast

import yaml

from lookout.application.errors import ConfigError
from lookout.domain.policy import Thresholds
from lookout.domain.stack import Stack, StackEntry

DEFAULT_CATEGORIES = ("security", "release", "breaking-change", "tooling", "ai", "industry", "other")


@dataclass(frozen=True, slots=True)
class LlmConfig:
    """The OpenAI-compatible endpoint."""

    base_url: str = "http://localhost:11434/v1"
    model: str = "llama3.1"
    api_key: str = ""
    daily_limit: int = 200
    summary_chars: int = 400


@dataclass(frozen=True, slots=True)
class PersonalizationConfig:
    """How fast the profile forgets and how much it needs before it learns."""

    half_life_days: int = 30
    minimum_signals: int = 5


@dataclass(frozen=True, slots=True)
class ScheduleConfig:
    """How often ``lookout serve`` runs by itself; 0 turns it off."""

    interval_minutes: int = 60


@dataclass(frozen=True, slots=True)
class GitHubConfig:
    """How GitHub is reached: ``auto`` prefers the local ``gh`` login, then ``LOOKOUT_GITHUB_TOKEN``."""

    via: str = "auto"


@dataclass(frozen=True, slots=True)
class SourceConfig:
    """One declared source."""

    name: str
    kind: str
    settings: dict[str, Any] = field(default_factory=dict[str, Any])
    keywords: tuple[str, ...] = ()
    enabled: bool = True


@dataclass(frozen=True, slots=True)
class Config:
    """Everything Lookout needs to run."""

    database: Path = Path("data/lookout.db")
    llm: LlmConfig = field(default_factory=LlmConfig)
    interests: str = ""
    categories: tuple[str, ...] = DEFAULT_CATEGORIES
    stack: Stack = field(default_factory=Stack)
    thresholds: Thresholds = field(default_factory=Thresholds)
    sources: tuple[SourceConfig, ...] = ()
    personalization: PersonalizationConfig = field(default_factory=PersonalizationConfig)
    schedule: ScheduleConfig = field(default_factory=ScheduleConfig)
    github: GitHubConfig = field(default_factory=GitHubConfig)
    dashboard_dir: Path = Path("frontend/dist")
    body_limit: int = 4000


def load_config(
    path: Path, supported_kinds: tuple[str, ...], environ: dict[str, str] | None = None
) -> Config:
    """Read and validate a configuration file. Secrets come from ``environ`` (``LOOKOUT_LLM_API_KEY``)."""
    env = environ or {}
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as error:
        msg = f"{path}: cannot read the configuration ({error.strerror}). Copy lookout.example.yaml to start."
        raise ConfigError(msg) from error
    try:
        raw: object = yaml.safe_load(text) or {}
    except yaml.YAMLError as error:
        msg = f"{path}: not valid YAML ({error})"
        raise ConfigError(msg) from error
    reader = _Reader(path)
    root = reader.mapping(raw, "the file")
    return Config(
        database=Path(reader.text(root, "database", "data/lookout.db")),
        llm=_llm(reader, reader.mapping(root.get("llm", {}), "llm"), env),
        interests=reader.text(root, "interests", ""),
        categories=reader.strings(root, "categories", DEFAULT_CATEGORIES),
        stack=_stack(reader, root.get("stack", [])),
        thresholds=_thresholds(reader, reader.mapping(root.get("thresholds", {}), "thresholds")),
        sources=_sources(reader, root.get("sources", []), supported_kinds),
        personalization=_personalization(
            reader, reader.mapping(root.get("personalization", {}), "personalization")
        ),
        schedule=ScheduleConfig(
            interval_minutes=reader.integer(
                reader.mapping(root.get("schedule", {}), "schedule"), "interval_minutes", 60
            )
        ),
        github=_github(reader, reader.mapping(root.get("github", {}), "github")),
        dashboard_dir=Path(reader.text(root, "dashboard_dir", "frontend/dist")),
        body_limit=reader.integer(root, "body_limit", 4000, minimum=100),
    )


class _Reader:
    def __init__(self, path: Path) -> None:
        self._path = path

    def error(self, message: str) -> ConfigError:
        return ConfigError(f"{self._path}: {message}")

    def fail(self, key: str, expected: str) -> ConfigError:
        return self.error(f"'{key}' must be {expected}")

    def mapping(self, value: object, key: str) -> dict[str, Any]:
        if not isinstance(value, dict):
            raise self.fail(key, "a mapping")
        return cast("dict[str, Any]", value)

    def text(self, data: dict[str, Any], key: str, default: str) -> str:
        value = data.get(key, default)
        if not isinstance(value, str):
            raise self.fail(key, "text")
        return value

    def integer(self, data: dict[str, Any], key: str, default: int, *, minimum: int = 0) -> int:
        value = data.get(key, default)
        if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
            raise self.fail(key, f"a whole number of at least {minimum}")
        return value

    def boolean(self, data: dict[str, Any], key: str, *, default: bool) -> bool:
        value = data.get(key, default)
        if not isinstance(value, bool):
            raise self.fail(key, "true or false")
        return value

    def strings(self, data: dict[str, Any], key: str, default: tuple[str, ...]) -> tuple[str, ...]:
        value = data.get(key, list(default))
        if not isinstance(value, list) or not all(isinstance(v, str) for v in cast("list[object]", value)):
            raise self.fail(key, "a list of text")
        return tuple(cast("list[str]", value))

    def sequence(self, value: object, key: str) -> list[dict[str, Any]]:
        if not isinstance(value, list):
            raise self.fail(key, "a list")
        return [self.mapping(v, f"{key}[{n}]") for n, v in enumerate(cast("list[object]", value))]


def _llm(reader: _Reader, data: dict[str, Any], env: dict[str, str]) -> LlmConfig:
    base = LlmConfig()
    return LlmConfig(
        base_url=reader.text(data, "base_url", base.base_url),
        model=reader.text(data, "model", base.model),
        api_key=env.get("LOOKOUT_LLM_API_KEY", ""),
        daily_limit=reader.integer(data, "daily_limit", base.daily_limit),
        summary_chars=reader.integer(data, "summary_chars", base.summary_chars, minimum=50),
    )


def _stack(reader: _Reader, raw: object) -> Stack:
    entries: list[StackEntry] = []
    for number, data in enumerate(reader.sequence(raw, "stack")):
        if not isinstance(data.get("name"), str) or not data["name"].strip():
            raise reader.error(f"stack[{number}] needs a 'name'")
        entries.append(
            StackEntry(
                name=data["name"],
                ecosystem=reader.text(data, "ecosystem", "other"),
                aliases=reader.strings(data, "aliases", ()),
            )
        )
    return Stack(tuple(entries))


def _personalization(reader: _Reader, data: dict[str, Any]) -> PersonalizationConfig:
    base = PersonalizationConfig()
    return PersonalizationConfig(
        half_life_days=reader.integer(data, "half_life_days", base.half_life_days, minimum=1),
        minimum_signals=reader.integer(data, "minimum_signals", base.minimum_signals),
    )


GITHUB_WAYS = ("auto", "gh", "token")


def _github(reader: _Reader, data: dict[str, Any]) -> GitHubConfig:
    via = reader.text(data, "via", "auto")
    if via not in GITHUB_WAYS:
        raise reader.fail("via", f"one of {', '.join(GITHUB_WAYS)}")
    return GitHubConfig(via=via)


def _thresholds(reader: _Reader, data: dict[str, Any]) -> Thresholds:
    base = Thresholds()
    found = Thresholds(
        p0=reader.integer(data, "p0", base.p0),
        p1=reader.integer(data, "p1", base.p1),
        p2=reader.integer(data, "p2", base.p2),
    )
    if not found.p0 > found.p1 > found.p2:
        raise reader.error("thresholds must satisfy p0 > p1 > p2")
    return found


def _sources(reader: _Reader, raw: object, supported: tuple[str, ...]) -> tuple[SourceConfig, ...]:
    sources: list[SourceConfig] = []
    for number, data in enumerate(reader.sequence(raw, "sources")):
        name, kind = data.get("name"), data.get("kind")
        if not isinstance(name, str) or not name.strip():
            raise reader.error(f"sources[{number}] needs a 'name'")
        if any(s.name == name for s in sources):
            raise reader.error(f"two sources are named '{name}'")
        if kind not in supported:
            raise reader.error(f"source '{name}' has kind {kind!r}; supported kinds: {', '.join(supported)}")
        settings = {k: v for k, v in data.items() if k not in {"name", "kind", "keywords", "enabled"}}
        sources.append(
            SourceConfig(
                name=name,
                kind=str(kind),
                settings=settings,
                keywords=reader.strings(data, "keywords", ()),
                enabled=reader.boolean(data, "enabled", default=True),
            )
        )
    return tuple(sources)
