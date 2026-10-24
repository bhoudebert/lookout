"""Scenarios of openspec/specs/cli (Configuration) and source-ingestion (Declared sources)."""

import re
from pathlib import Path
from typing import Any

import pytest
import yaml

from lookout.application.errors import ConfigError
from lookout.bootstrap.config import DEFAULT_KINDS
from lookout.bootstrap.container import SOURCE_TYPES, build, load
from lookout.domain.policy import Thresholds


def write(tmp_path: Path, data: object) -> Path:
    path = tmp_path / "lookout.yaml"
    path.write_text(data if isinstance(data, str) else yaml.safe_dump(data))
    return path


def test_empty_file_gives_the_defaults(tmp_path: Path) -> None:
    config = load(write(tmp_path, ""))
    assert config.kinds == DEFAULT_KINDS
    assert config.thresholds == Thresholds()
    assert config.llm.base_url == "http://localhost:11434/v1"
    assert (config.sources, config.stack.entries) == ((), ())


def test_full_file_is_read(tmp_path: Path) -> None:
    config = load(
        write(
            tmp_path,
            {
                "database": "x/y.db",
                "interests": "rust",
                "kinds": ["a", "b"],
                "body_limit": 500,
                "llm": {"base_url": "http://h/v1", "model": "m", "daily_limit": 5, "summary_chars": 100},
                "thresholds": {"p0": 95, "p1": 80, "p2": 50},
                "personalization": {"half_life_days": 7, "minimum_signals": 2},
                "stack": [{"name": "postgresql", "ecosystem": "other", "aliases": ["postgres"]}],
                "sources": [
                    {"name": "a", "type": "rss", "url": "https://a", "keywords": ["x"], "enabled": False},
                ],
            },
        ),
        {"LOOKOUT_LLM_API_KEY": "secret"},
    )
    assert (config.database, config.interests, config.kinds, config.body_limit) == (
        Path("x/y.db"),
        "rust",
        ("a", "b"),
        500,
    )
    assert (config.llm.model, config.llm.api_key, config.llm.daily_limit) == ("m", "secret", 5)
    assert config.thresholds == Thresholds(95, 80, 50)
    assert (config.personalization.half_life_days, config.personalization.minimum_signals) == (7, 2)
    assert config.stack.entries[0].aliases == ("postgres",)
    (source,) = config.sources
    assert (source.keywords, source.enabled, source.settings) == (("x",), False, {"url": "https://a"})


def test_unknown_type_names_the_source_and_lists_the_types(tmp_path: Path) -> None:
    path = write(tmp_path, {"sources": [{"name": "files", "type": "ftp"}]})
    with pytest.raises(ConfigError) as error:
        load(path)
    message = str(error.value)
    assert str(path) in message
    assert "'files'" in message
    assert "'ftp'" in message
    assert ", ".join(SOURCE_TYPES) in message


def test_missing_file_says_how_to_start(tmp_path: Path) -> None:
    with pytest.raises(ConfigError, match=r"lookout\.example\.yaml"):
        load(tmp_path / "nope.yaml")


def test_invalid_yaml_is_reported(tmp_path: Path) -> None:
    with pytest.raises(ConfigError, match="not valid YAML"):
        load(write(tmp_path, "a: [unclosed"))


@pytest.mark.parametrize(
    ("data", "fragment"),
    [
        ("- just\n- a list\n", "'the file' must be a mapping"),
        ({"database": ["x"]}, "'database' must be text"),
        ({"llm": []}, "'llm' must be a mapping"),
        ({"llm": {"daily_limit": "many"}}, "'daily_limit' must be a whole number"),
        ({"llm": {"daily_limit": True}}, "'daily_limit' must be a whole number"),
        ({"llm": {"summary_chars": 5}}, "'summary_chars' must be a whole number of at least 50"),
        ({"kinds": "security"}, "'kinds' must be a list of text"),
        ({"kinds": [1]}, "'kinds' must be a list of text"),
        ({"stack": {"name": "x"}}, "'stack' must be a list"),
        ({"stack": ["django"]}, "'stack[0]' must be a mapping"),
        ({"stack": [{"ecosystem": "pypi"}]}, "stack[0] needs a 'name'"),
        ({"stack": [{"name": " "}]}, "stack[0] needs a 'name'"),
        ({"thresholds": {"p0": 50, "p1": 60, "p2": 10}}, "p0 > p1 > p2"),
        ({"sources": [{"type": "rss"}]}, "sources[0] needs a 'name'"),
        (
            {"sources": [{"name": "a", "type": "rss"}, {"name": "a", "type": "rss"}]},
            "two sources are named 'a'",
        ),
        ({"sources": [{"name": "a", "type": "rss", "enabled": "yes"}]}, "'enabled' must be true or false"),
        ({"personalization": {"half_life_days": 0}}, "'half_life_days' must be a whole number of at least 1"),
        ({"body_limit": 5}, "'body_limit' must be a whole number of at least 100"),
    ],
)
def test_wrong_shapes_name_the_key_and_the_expected_form(tmp_path: Path, data: Any, fragment: str) -> None:
    with pytest.raises(ConfigError, match=re.escape(fragment)):
        load(write(tmp_path, data))


def test_rss_source_without_a_url_fails_at_wiring(tmp_path: Path) -> None:
    config = load(
        write(tmp_path, {"database": str(tmp_path / "db"), "sources": [{"name": "a", "type": "rss"}]})
    )
    with pytest.raises(ConfigError, match=r"source 'a' .rss. needs a 'url'"):
        build(config)


def test_paths_can_come_from_the_environment_and_the_file_wins(tmp_path: Path) -> None:
    env = {"LOOKOUT_DATABASE": "/data/lookout.db", "LOOKOUT_DASHBOARD_DIR": "/app/dashboard"}
    config = load(write(tmp_path, ""), env)
    assert (config.database, config.dashboard_dir) == (Path("/data/lookout.db"), Path("/app/dashboard"))
    explicit = load(write(tmp_path, {"database": "mine.db", "dashboard_dir": "mine"}), env)
    assert (explicit.database, explicit.dashboard_dir) == (Path("mine.db"), Path("mine"))


def test_channels_and_kinds_are_read_and_other_always_exists(tmp_path: Path) -> None:
    config = load(
        write(
            tmp_path,
            {
                "kinds": ["release", "schedule"],
                "channels": [{"name": "AI", "description": "Models"}, {"name": " Rust "}],
                "sources": [{"name": "a", "type": "rss", "url": "https://a", "channels": ["AI"]}],
            },
        ),
        {},
    )
    assert config.kinds == ("release", "schedule")
    assert [(c.name, c.description) for c in config.channels] == [
        ("AI", "Models"),
        ("Rust", ""),
        ("Other", ""),
    ]
    assert config.sources[0].channels == ("AI",)


def test_the_defaults_have_the_kinds_and_only_other(tmp_path: Path) -> None:
    config = load(write(tmp_path, ""), {})
    assert [c.name for c in config.channels] == ["Other"]
    assert {"release", "security", "api-change", "schedule", "other"} <= set(config.kinds)


@pytest.mark.parametrize(
    ("data", "message"),
    [
        ({"channels": [{"description": "x"}]}, "channels[0] needs a 'name'"),
        ({"channels": [{"name": "AI"}, {"name": "ai"}]}, "two channels are named 'ai'"),
        ({"channels": "AI"}, "'channels' must be a list"),
        ({"channels": [{"name": "AI", "description": 3}]}, "'description' must be text"),
        ({"kinds": "release"}, "'kinds' must be a list of text"),
    ],
)
def test_bad_channels_and_kinds_are_refused(tmp_path: Path, data: Any, message: str) -> None:
    with pytest.raises(ConfigError, match=re.escape(message)):
        load(write(tmp_path, data), {})


def test_a_source_feeding_an_undeclared_channel_is_refused_when_wiring(tmp_path: Path) -> None:
    data = {
        "database": str(tmp_path / "db"),
        "channels": [{"name": "AI"}],
        "sources": [{"name": "a", "type": "rss", "url": "https://a", "channels": ["Gardening"]}],
    }
    with pytest.raises(ConfigError, match="source 'a' feeds the channel 'Gardening', which is not declared"):
        build(load(write(tmp_path, data), {}))


def test_a_declared_other_channel_keeps_its_description_and_is_not_added_twice(tmp_path: Path) -> None:
    config = load(write(tmp_path, {"channels": [{"name": "other", "description": "Everything else"}]}), {})
    assert [(c.name, c.description) for c in config.channels] == [("other", "Everything else")]
