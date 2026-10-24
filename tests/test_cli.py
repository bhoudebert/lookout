"""The command line: scenarios from openspec/specs/cli."""

import sys

import pytest
from typer.testing import CliRunner

from lookout.adapters.cli.app import app, main

runner = CliRunner()


def test_version_prints_the_installed_version() -> None:
    result = runner.invoke(app, ["version"])
    assert result.exit_code == 0
    assert result.output.strip() != ""


def test_no_arguments_shows_help() -> None:
    result = runner.invoke(app, [])
    assert "Usage" in result.output


def test_console_script_runs_the_app(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sys, "argv", ["lookout", "version"])
    with pytest.raises(SystemExit) as stop:
        main()
    assert stop.value.code == 0
