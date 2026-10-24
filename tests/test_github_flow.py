"""GitHub sources through the whole application (openspec: github-sources, priority)."""

from pathlib import Path

import pytest
import yaml
from tests.cli_support import Lookout, reading
from tests.github_support import FakeGitHub

from lookout.adapters.sources.github import repo_path
from lookout.application.errors import ConfigError
from lookout.application.github import GitHubError
from lookout.bootstrap.container import build, load

GITHUB = {"name": "gh-watch", "type": "github", "repos": ["o/r"], "watch": ["advisories", "dependabot"]}


def watching(tmp_path: Path, github: FakeGitHub | None = None) -> Lookout:
    lookout = Lookout(tmp_path, github=github, sources=[GITHUB])
    lookout.network.chat = lambda _request: reading(score=5)
    return lookout


def test_a_critical_advisory_on_a_declared_package_is_p0_whatever_the_model_says(tmp_path: Path) -> None:
    lookout = watching(tmp_path)
    lookout("run")
    line = next(row for row in lookout("inbox").splitlines() if "SQL injection" in row)
    assert line.startswith("P0")
    assert "GHSA-aaaa-bbbb-cccc" in line
    why = lookout("explain", line.split()[2])
    assert "rule: critical advisory GHSA-aaaa-bbbb-cccc, CVE-2026-1234 affects Django, which you use" in why


def test_a_dependabot_alert_on_a_watched_repository_is_at_least_p1(tmp_path: Path) -> None:
    lookout = watching(tmp_path)
    lookout("run")
    line = next(row for row in lookout("inbox").splitlines() if "Dependabot alert" in row)
    assert line.startswith("P1")
    assert "in a repository you watch" in lookout("explain", line.split()[2])


def test_an_item_the_model_has_not_read_still_gets_its_rule_priority(tmp_path: Path) -> None:
    lookout = watching(tmp_path)
    lookout.network.llm_down = True
    lookout("run")
    assert next(row for row in lookout("inbox").splitlines() if "SQL injection" in row).startswith("P0")


def test_without_gh_or_a_token_only_the_github_source_fails(tmp_path: Path) -> None:
    lookout = Lookout(
        tmp_path,
        github=FakeGitHub(via="unavailable", error=GitHubError("log in with `gh auth login`")),
        sources=[
            {"name": "blog", "type": "rss", "url": "https://example.com/feed"},
            GITHUB,
        ],
    )
    output = lookout("run")
    assert "blog: 3 entries, 3 new" in output
    assert "gh-watch: FAILED o/r advisories: log in with `gh auth login`" in output


def test_doctor_reports_how_github_is_reached(tmp_path: Path) -> None:
    assert "ok   github: reading through your gh login" in watching(tmp_path)("doctor")
    token = (
        watching(tmp_path / "t", github=FakeGitHub(via="token")) if (tmp_path / "t").mkdir() is None else None
    )
    assert token is not None
    assert "ok   github: reading through a token" in token("doctor")


def test_doctor_fails_when_github_cannot_be_reached(tmp_path: Path) -> None:
    lookout = watching(tmp_path, FakeGitHub(via="unavailable", error=GitHubError("nope")))
    output = lookout("doctor", exit_code=1)
    assert "FAIL github:" in output
    assert "gh auth login" in output
    assert "FAIL source gh-watch: o/r advisories: nope" in output


def test_doctor_says_nothing_about_github_when_no_source_uses_it(tmp_path: Path) -> None:
    assert "github" not in Lookout(tmp_path)("doctor")


def write(tmp_path: Path, source: dict[str, object], github: object | None = None) -> Path:
    path = tmp_path / "lookout.yaml"
    data: dict[str, object] = {
        "database": str(tmp_path / "db"),
        "sources": [{"name": "g", "type": "github", **source}],
    }
    if github is not None:
        data["github"] = github
    path.write_text(yaml.safe_dump(data))
    return path


@pytest.mark.parametrize(
    ("source", "message"),
    [
        ({}, "needs 'repos'"),
        ({"repos": []}, "needs 'repos'"),
        ({"repos": "o/r"}, "needs 'repos'"),
        ({"repos": [1]}, "needs 'repos'"),
        ({"repos": ["no-slash"]}, "'no-slash' is not of the form owner/name"),
        ({"repos": ["o/r"], "watch": ["releases", "stars"]}, "'watch' must be a list of"),
        ({"repos": ["o/r"], "watch": []}, "'watch' must be a list of"),
        ({"repos": ["o/r"], "watch": "releases"}, "'watch' must be a list of"),
    ],
)
def test_github_sources_are_validated_when_wiring(
    tmp_path: Path, source: dict[str, object], message: str
) -> None:
    with pytest.raises(ConfigError, match=message):
        build(load(write(tmp_path, source), {}), github=FakeGitHub())


@pytest.mark.parametrize(
    ("typed", "repo"),
    [
        ("https://github.com/bhoudebert/agent-motoride/", "bhoudebert/agent-motoride"),
        ("https://github.com/bhoudebert/mobile-motoride", "bhoudebert/mobile-motoride"),
        ("http://www.github.com/o/r/issues/12?x=1#top", "o/r"),
        ("github.com/o/r.git", "o/r"),
        ("git@github.com:o/r.git", "o/r"),
        ("  o/r  ", "o/r"),
        ("o/r.js", "o/r.js"),
    ],
)
def test_repo_path_reads_what_people_paste(typed: str, repo: str) -> None:
    assert repo_path(typed) == repo


def test_pasted_urls_are_what_gets_asked_of_github_and_twice_the_same_repo_is_asked_once(
    tmp_path: Path,
) -> None:
    fake = FakeGitHub()
    urls = ["https://github.com/o/a/", "git@github.com:o/b.git", "o/a"]
    lookout = Lookout(
        tmp_path, github=fake, sources=[{"name": "g", "type": "github", "repos": urls, "watch": ["releases"]}]
    )
    lookout.network.chat = lambda _request: reading(score=5)
    lookout("run")
    assert fake.asked == ["o/a", "o/b"]


@pytest.mark.parametrize(
    "typed", ["https://example.com/o/r", "https://github.com/onlyowner", "https://github.com/"]
)
def test_a_url_that_is_not_a_repository_is_still_refused(tmp_path: Path, typed: str) -> None:
    with pytest.raises(ConfigError, match="is not of the form owner/name"):
        build(load(write(tmp_path, {"repos": [typed]}), {}), github=FakeGitHub())


def test_github_sources_default_to_releases_and_advisories(tmp_path: Path) -> None:
    container = build(load(write(tmp_path, {"repos": ["o/r"]}), {}), github=FakeGitHub())
    try:
        assert container.github_via == "gh"
        assert len(container.fetchers()) == 1
    finally:
        container.close()


def test_the_way_to_reach_github_is_chosen_from_the_environment(tmp_path: Path) -> None:
    config = load(write(tmp_path, {"repos": ["o/r"]}, {"via": "token"}), {})
    container = build(config, environ={"LOOKOUT_GITHUB_TOKEN": "t"})
    try:
        assert container.github_via == "token"
    finally:
        container.close()


def test_an_unknown_way_to_reach_github_is_refused(tmp_path: Path) -> None:
    with pytest.raises(ConfigError, match="'via' must be one of auto, gh, token"):
        load(write(tmp_path, {"repos": ["o/r"]}, {"via": "carrier-pigeon"}), {})
