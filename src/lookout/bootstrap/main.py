"""The ``lookout`` console script: the real wiring of the command line."""

import os
from pathlib import Path

from lookout.adapters.cli.app import create_app
from lookout.application.services import Services
from lookout.bootstrap.container import build, load


def open_services(path: Path) -> Services:
    """Read the configuration at ``path`` and wire the application."""
    return build(load(path, dict(os.environ))).services()


app = create_app(open_services)


def main() -> None:
    """Console script entry point."""
    app()
