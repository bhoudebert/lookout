"""The scheduler and the serve command (openspec: scheduling, cli)."""

import threading
from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest
from fastapi import FastAPI
from tests.cli_support import Lookout, http_client

from lookout.adapters.scheduler.periodic import Periodic
from lookout.bootstrap.main import serve


def test_the_periodic_action_runs_until_stopped() -> None:
    ticks = threading.Event()
    calls: list[int] = []

    def action() -> None:
        calls.append(1)
        if len(calls) >= 3:
            ticks.set()

    periodic = Periodic(0.01, action)
    periodic.start()
    assert ticks.wait(timeout=5)
    periodic.stop()
    count = len(calls)
    assert count >= 3
    assert len(calls) == count


def test_serving_starts_the_schedule_and_stops_it_afterwards(tmp_path: Path) -> None:
    lookout = Lookout(tmp_path)
    services = replace(lookout.services(), schedule_minutes=1)
    seen: dict[str, Any] = {}

    def fake_server(api: FastAPI, **options: Any) -> None:
        seen["options"] = options
        client = http_client(api)
        seen["health"] = client.get("/api/health").json()["status"]

    try:
        serve(services, "0.0.0.0", 9000, run_server=fake_server)  # noqa: S104
    finally:
        services.close()
    assert seen["options"] == {"host": "0.0.0.0", "port": 9000, "log_level": "info"}  # noqa: S104
    assert seen["health"] == "ok"


def test_serving_without_a_schedule(tmp_path: Path) -> None:
    services = replace(Lookout(tmp_path).services(), schedule_minutes=0)
    started: list[bool] = []

    def fake_server(api: FastAPI, **options: Any) -> None:
        started.append(True)

    try:
        serve(services, "127.0.0.1", 1, run_server=fake_server)
    finally:
        services.close()
    assert started == [True]


def test_a_failing_server_still_stops_the_schedule(tmp_path: Path) -> None:
    services = replace(Lookout(tmp_path).services(), schedule_minutes=1)

    def broken(api: FastAPI, **options: Any) -> None:
        msg = "port in use"
        raise OSError(msg)

    try:
        with pytest.raises(OSError, match="port in use"):
            serve(services, "127.0.0.1", 1, run_server=broken)
    finally:
        services.close()


def test_the_serve_command_passes_host_and_port(tmp_path: Path) -> None:
    lookout = Lookout(tmp_path)
    lookout("serve")
    lookout("serve", "--host", "0.0.0.0", "--port", "1234")  # noqa: S104
    assert lookout.served == [("127.0.0.1", 8899), ("0.0.0.0", 1234)]  # noqa: S104
