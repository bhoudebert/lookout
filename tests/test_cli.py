"""The command line end to end (openspec: cli). Real wiring and SQLite; the network is scripted."""

import json
import sys
from pathlib import Path

import httpx
import pytest
from tests.cli_support import FEED_URL, Lookout, reading, runner

from lookout.adapters.clock import SystemClock
from lookout.bootstrap import main as entry


def test_no_arguments_shows_help(tmp_path: Path) -> None:
    result = runner.invoke(Lookout(tmp_path).app, [])
    assert "Usage" in result.output
    assert "doctor" in result.output


def test_version_prints_the_installed_version(tmp_path: Path) -> None:
    assert Lookout(tmp_path)("version").strip() != ""


def test_run_fetches_reads_and_fills_the_inbox(tmp_path: Path) -> None:
    lookout = Lookout(tmp_path)
    output = lookout("run")
    assert "blog: 3 entries, 3 new" in output
    assert "read 3, failed 0, waiting for budget 0" in output
    inbox = lookout("inbox")
    assert "P1" in inbox
    assert "Django 6.0 released" in inbox
    assert "3 of 3" in inbox


def test_running_again_finds_nothing_new(tmp_path: Path) -> None:
    lookout = Lookout(tmp_path)
    lookout("run")
    assert "blog: 3 entries, 0 new" in lookout("run")


def test_a_failing_source_is_reported_then_backs_off(tmp_path: Path) -> None:
    lookout = Lookout(tmp_path)
    lookout.network.feed = 503
    assert "blog: FAILED" in lookout("run")
    assert "blog: backing off after an error" in lookout("run")


def test_model_down_leaves_items_flagged_not_lost(tmp_path: Path) -> None:
    lookout = Lookout(tmp_path)
    lookout.network.llm_down = True
    assert "read 0, failed 3" in lookout("run")
    assert "3 of 3" in lookout("inbox")


def test_inbox_filters(tmp_path: Path) -> None:
    lookout = Lookout(tmp_path)
    lookout.network.chat = lambda request: reading(
        score=95 if "Django" in request.content.decode() else 10,
    )
    lookout("run")
    assert "1 of 1" in lookout("inbox", "--priority", "p0")
    assert "Django" in lookout("inbox", "-p", "P0", "-p", "P3")
    assert "3 of 3" in lookout("inbox", "--channel", "Other")
    assert "3 of 3" in lookout("inbox", "--source", "blog")
    assert "0 of 0" in lookout("inbox", "--source", "elsewhere")
    assert "1 of 1" in lookout("inbox", "--text", "django")
    assert "0 of 0" in lookout("inbox", "--starred")
    assert "0 of 0" in lookout("inbox", "--state", "done")


def test_unknown_priority_is_refused(tmp_path: Path) -> None:
    assert "unknown priority 'P9'" in Lookout(tmp_path)("inbox", "-p", "P9", exit_code=1)


def first_id(lookout: Lookout, *extra: str) -> str:
    return lookout("inbox", *extra).splitlines()[0].split()[2]


def test_acting_on_items(tmp_path: Path) -> None:
    lookout = Lookout(tmp_path)
    lookout("run")
    item = first_id(lookout)
    assert "[seen]" in lookout("act", item, "open")
    assert "*" in lookout("act", item, "star").split()[1]
    assert "[done]" in lookout("act", item, "done")
    assert "2 of 2" in lookout("inbox")
    assert "[seen]" in lookout("act", item, "reopen")
    assert "[dismissed]" in lookout("act", item, "dismiss")


def test_snooze_hides_until_the_time_passes(tmp_path: Path) -> None:
    lookout = Lookout(tmp_path)
    lookout("run")
    item = first_id(lookout)
    assert "[snoozed]" in lookout("act", item, "snooze", "--hours", "2")
    assert "2 of 2" in lookout("inbox")
    lookout.clock.advance(hours=3)
    assert "3 of 3" in lookout("inbox")


def test_snooze_until_a_date(tmp_path: Path) -> None:
    lookout = Lookout(tmp_path)
    lookout("run")
    item = first_id(lookout)
    lookout("act", item, "snooze", "--until", "2026-10-25T09:00:00+00:00")
    lookout("act", first_id(lookout), "snooze", "--until", "2026-10-25T09:00:00")
    lookout.clock.advance(days=1, minutes=1)
    assert "3 of 3" in lookout("inbox")


def test_bad_snooze_date_and_bad_ids_are_refused(tmp_path: Path) -> None:
    lookout = Lookout(tmp_path)
    lookout("run")
    item = first_id(lookout)
    assert "cannot read 'tomorrow'" in lookout("act", item, "snooze", "--until", "tomorrow", exit_code=1)
    assert "no item nope" in lookout("act", "nope", "done", exit_code=1)
    assert "already in the inbox" in lookout("act", item, "reopen", exit_code=1)


def test_doctor_reports_each_check(tmp_path: Path) -> None:
    output = Lookout(tmp_path)("doctor")
    assert "ok   database:" in output
    assert "ok   llm: http://localhost:11434/v1 serves llama3.1" in output
    assert "ok   source blog: 3 entries" in output


def test_doctor_says_what_to_do_when_ollama_is_not_running(tmp_path: Path) -> None:
    lookout = Lookout(tmp_path)
    lookout.network.llm_down = True
    output = lookout("doctor", exit_code=1)
    assert "FAIL llm:" in output
    assert "connection refused" in output
    assert "ollama serve" in output


def test_doctor_accepts_a_model_that_ollama_lists_with_its_latest_tag(tmp_path: Path) -> None:
    lookout = Lookout(tmp_path)
    lookout.network.models = {"data": [{"id": "llama3.1:latest"}]}
    assert "ok   llm: http://localhost:11434/v1 serves llama3.1" in lookout("doctor")


def test_doctor_names_the_model_to_pull(tmp_path: Path) -> None:
    lookout = Lookout(tmp_path)
    lookout.network.models = {"data": [{"id": "other"}]}
    assert "ollama pull llama3.1" in lookout("doctor", exit_code=1)


def test_doctor_without_hint_for_remote_endpoints_and_odd_answers(tmp_path: Path) -> None:
    remote = Lookout(tmp_path, llm={"base_url": "https://api.example.com/v1"})
    output = remote("doctor", exit_code=1)
    assert "FAIL llm:" in output
    assert "ollama serve" not in output


def test_doctor_with_an_unreadable_model_list(tmp_path: Path) -> None:
    lookout = Lookout(tmp_path)
    lookout.network.models = ["not", "a", "mapping"]
    assert "FAIL llm:" in lookout("doctor", exit_code=1)


def test_doctor_flags_failing_sources_and_missing_sources(tmp_path: Path) -> None:
    lookout = Lookout(tmp_path)
    lookout.network.feed = 500
    assert "FAIL source blog:" in lookout("doctor", exit_code=1)
    empty = Lookout(tmp_path / "empty", sources=[]) if (tmp_path / "empty").mkdir() is None else lookout
    assert "no source is enabled" in empty("doctor", exit_code=1)


def test_demo_fills_the_inbox_once(tmp_path: Path) -> None:
    lookout = Lookout(tmp_path)
    assert "added 6 demo items" in lookout("demo")
    assert "added 0 demo items" in lookout("demo")
    assert "P0" in lookout("inbox").splitlines()[0]


def test_reassess_applies_a_new_stack_without_the_model(tmp_path: Path) -> None:
    lookout = Lookout(tmp_path, stack=[])
    lookout("demo")
    assert "0 items changed" in lookout("reassess")
    lookout.config["stack"] = [{"name": "django"}]
    lookout.write()
    assert "1 items changed" in lookout("reassess")
    assert "rule: critical advisory CVE-2026-1234" in lookout("export")


def test_explain_and_forget(tmp_path: Path) -> None:
    lookout = Lookout(tmp_path, personalization={"minimum_signals": 1})
    lookout("run")
    ids = [line.split()[2] for line in lookout("inbox").splitlines()[:-1]]
    for item in ids[:2]:
        lookout("act", item, "star")
    why = lookout("explain", ids[2])
    assert "model score 75" in why
    assert "your profile moves it +" in why
    assert "source:blog" in why
    assert "profile reset" in lookout("forget")
    assert "your profile moves it +0" in lookout("explain", ids[2])
    assert "no item nope" in lookout("explain", "nope", exit_code=1)


def test_explaining_an_item_the_model_has_not_read(tmp_path: Path) -> None:
    lookout = Lookout(tmp_path)
    lookout.network.llm_down = True
    lookout("run")
    why = lookout("explain", first_id(lookout))
    assert "model score" not in why
    assert "not yet assessed" in why or "no rule matched" in why


def test_export_prints_json_lines(tmp_path: Path) -> None:
    lookout = Lookout(tmp_path)
    lookout("demo")
    lines = lookout("export").splitlines()
    assert len(lines) == 6
    assert all("title" in json.loads(line) for line in lines)


def test_missing_configuration_is_explained(tmp_path: Path) -> None:
    lookout = Lookout(tmp_path)
    lookout.path.unlink()
    assert "lookout.example.yaml" in lookout("inbox", exit_code=1)


def test_configuration_path_can_come_from_the_environment(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    lookout = Lookout(tmp_path)
    monkeypatch.setenv("LOOKOUT_CONFIG", str(lookout.path))
    result = runner.invoke(lookout.app, ["demo"])
    assert result.exit_code == 0


def test_the_real_wiring_runs_offline_with_no_sources(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    config = tmp_path / "lookout.yaml"
    config.write_text(f"database: {tmp_path / 'real.db'}\n")
    monkeypatch.setattr(sys, "argv", ["lookout", "--config", str(config), "demo"])
    with pytest.raises(SystemExit) as stop:
        entry.main()
    assert stop.value.code == 0
    assert (tmp_path / "real.db").exists()


def test_the_system_clock_is_timezone_aware() -> None:
    assert SystemClock().now().tzinfo is not None


def test_feed_url_constant_matches_the_fixture_network(tmp_path: Path) -> None:
    lookout = Lookout(tmp_path)
    lookout("run")
    assert any(str(r.url) == FEED_URL for r in lookout.network.requests)
    assert isinstance(lookout.network.requests[0], httpx.Request)


def test_the_inbox_shows_and_filters_by_category_including_what_is_under_it(tmp_path: Path) -> None:
    lookout = Lookout(
        tmp_path, channels=[{"name": "Dev > Rust"}, {"name": "Dev > Web"}, {"name": "Security"}]
    )
    lookout("demo")
    everything = lookout("inbox", "--limit", "20")
    assert "osv, Security" in everything
    assert "hn, Dev > Rust" in everything
    assert "1 of 1" in lookout("inbox", "--channel", "Dev > Rust")
    assert "2 of 2" in lookout("inbox", "--channel", "Dev")
    assert "2 of 2" in lookout("inbox", "--channel", "Security")
    assert "1 of 1" in lookout("inbox", "--channel", "Dev > Rust", "--channel", "Nope")
    assert "0 of 0" in lookout("inbox", "--channel", "Nope")
