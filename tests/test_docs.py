"""The documentation cannot drift from the code (docs/EVOLVING.md, step 5)."""

import dataclasses
import importlib.util
from pathlib import Path

from lookout.bootstrap.config import Config
from lookout.bootstrap.container import load

ROOT = Path(__file__).parent.parent


def _reference() -> str:
    spec = importlib.util.spec_from_file_location("reference", ROOT / "scripts" / "reference.py")
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return str(module.render())


def test_the_command_reference_matches_the_command_line() -> None:
    committed = (ROOT / "docs" / "guide" / "reference" / "commands.md").read_text()
    assert committed == _reference(), "run `just reference` and commit the page"


def test_every_command_is_in_the_reference() -> None:
    page = _reference()
    for command in (
        "run",
        "inbox",
        "act",
        "serve",
        "doctor",
        "demo",
        "reassess",
        "explain",
        "forget",
        "export",
    ):
        assert f"## `lookout {command}`" in page


def test_every_configuration_key_is_documented() -> None:
    page = (ROOT / "docs" / "guide" / "configuration.md").read_text()
    missing = [f.name for f in dataclasses.fields(Config) if f"`{f.name}`" not in page]
    assert missing == []


def test_the_example_configuration_loads() -> None:
    config = load(ROOT / "lookout.example.yaml")
    assert len(config.sources) >= 1
    assert config.stack.entries
