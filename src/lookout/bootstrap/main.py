"""The ``lookout`` console script: the real wiring of the command line."""

import os
from collections.abc import Callable
from pathlib import Path

import uvicorn

from lookout.adapters.cli.app import create_app
from lookout.adapters.http.app import create_app as create_api
from lookout.adapters.scheduler.periodic import Periodic
from lookout.application.services import Services
from lookout.bootstrap.container import build, load


def open_services(path: Path) -> Services:
    """Read the configuration at ``path`` and wire the application."""
    return build(load(path, dict(os.environ)), environ=os.environ).services()


def serve(
    services: Services,
    host: str,
    port: int,
    run_server: Callable[..., None] = uvicorn.run,
) -> None:
    """Serve the API and dashboard; run on the schedule while serving."""
    api = create_api(services, services.dashboard_dir)
    schedule = (
        Periodic(services.schedule_minutes * 60, services.runs.start)
        if services.schedule_minutes > 0
        else None
    )
    if schedule is not None:
        schedule.start()
    try:
        run_server(api, host=host, port=port, log_level="info")
    finally:
        if schedule is not None:
            schedule.stop()


app = create_app(open_services, serve)


def main() -> None:
    """Console script entry point."""
    app()
