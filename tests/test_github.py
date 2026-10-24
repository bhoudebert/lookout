"""Scenarios of openspec/specs/github-sources: parsing, gateways, the fetcher, rules and wiring."""

from datetime import UTC, datetime
from pathlib import Path

import httpx
import pytest
from tests.github_support import FakeGitHub, fixture, install_fake_gh

from lookout.adapters.github import parse
from lookout.adapters.github.gh_cli import GhCliGateway, gh_is_logged_in
from lookout.adapters.github.rest import USER_AGENT, RestGateway
from lookout.adapters.github.unavailable import REASON, UnavailableGateway
from lookout.adapters.sources.github import GitHubFetcher
from lookout.application.github import GitHubError
from lookout.application.ports_sources import SourceError
from lookout.bootstrap.container import choose_gateway
from lookout.domain.severity import Severity

# --- parsing: GitHub's JSON is outside input -------------------------------------------------------------


def test_releases_skip_drafts_and_entries_without_a_url() -> None:
    found = parse.releases(fixture("releases.json"))
    assert [r.tag for r in found] == ["v2.1.0", "v2.2.0-rc1"]
    first, second = found
    assert first.published_at == datetime(2026, 10, 22, 10, tzinfo=UTC)
    assert (second.prerelease, second.name, second.published_at) == (True, "v2.2.0-rc1", None)


def test_advisories_keep_ranges_and_survive_junk() -> None:
    first, second = parse.advisories(fixture("advisories.json"))
    assert (first.identifier, first.cve, first.severity) == (
        "GHSA-aaaa-bbbb-cccc",
        "CVE-2026-1234",
        "critical",
    )
    (affected,) = first.vulnerabilities
    assert (affected.package, affected.ecosystem, affected.vulnerable, affected.patched) == (
        "Django",
        "pip",
        "< 5.2.9",
        "5.2.9",
    )
    assert (second.cve, second.vulnerabilities) == (None, ())


def test_dependabot_alerts_read_the_nested_advisory() -> None:
    (alert,) = parse.dependabot_alerts(fixture("dependabot.json"))
    assert (alert.identifier, alert.severity, alert.summary) == (
        "GHSA-gggg-hhhh-iiii",
        "high",
        "PKCS12 parsing flaw",
    )
    (affected,) = alert.vulnerabilities
    assert (affected.package, affected.patched) == ("cryptography", "44.0.1")


@pytest.mark.parametrize("reader", [parse.releases, parse.advisories, parse.dependabot_alerts])
def test_an_answer_that_is_not_a_list_is_an_error(reader: object) -> None:
    with pytest.raises(GitHubError, match="not a list"):
        reader({"message": "Not Found"})  # type: ignore[operator]


def test_a_dependabot_alert_without_a_vulnerability_has_no_package() -> None:
    payload = [
        {
            "html_url": "https://x/1",
            "security_advisory": {"ghsa_id": "G", "severity": "low"},
            "security_vulnerability": None,
        }
    ]
    (alert,) = parse.dependabot_alerts(payload)
    assert alert.vulnerabilities == ()


# --- the gh executable ------------------------------------------------------------------------------------


def test_gh_reads_every_kind(tmp_path: Path) -> None:
    gateway = GhCliGateway(install_fake_gh(tmp_path))
    assert gateway.via == "gh"
    assert len(gateway.releases("o/r")) == 2
    assert len(gateway.advisories("o/r")) == 2
    assert len(gateway.dependabot_alerts("o/r")) == 1


def test_gh_errors_carry_its_message(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    gateway = GhCliGateway(install_fake_gh(tmp_path))
    monkeypatch.setenv("FAKE_GH_DENY_DEPENDABOT", "1")
    with pytest.raises(GitHubError, match="Resource not accessible"):
        gateway.dependabot_alerts("o/r")
    with pytest.raises(GitHubError, match="Not Found"):
        gateway.releases("o/missing")


def test_gh_answering_with_text_is_an_error(tmp_path: Path) -> None:
    with pytest.raises(GitHubError, match="not JSON"):
        GhCliGateway(install_fake_gh(tmp_path)).releases("o/garbage")


def test_a_missing_gh_is_an_error_not_a_crash(tmp_path: Path) -> None:
    with pytest.raises(GitHubError, match="gh api"):
        GhCliGateway(str(tmp_path / "nope")).releases("o/r")


def test_a_slow_gh_times_out(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("FAKE_GH_SLEEP", "5")
    with pytest.raises(GitHubError, match="timed out"):
        GhCliGateway(install_fake_gh(tmp_path), timeout=0.2).releases("o/r")


def test_login_detection(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    executable = install_fake_gh(tmp_path)
    assert gh_is_logged_in(executable) is True
    monkeypatch.setenv("FAKE_GH_AUTH", "1")
    assert gh_is_logged_in(executable) is False
    assert gh_is_logged_in(str(tmp_path / "nope")) is False


# --- the REST API -----------------------------------------------------------------------------------------


class Api:
    def __init__(self) -> None:
        self.requests: list[httpx.Request] = []
        self.responses: list[httpx.Response] = []

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        return self.responses.pop(0)

    def gateway(self) -> RestGateway:
        return RestGateway(httpx.Client(transport=httpx.MockTransport(self)), "tok")


def test_rest_sends_the_token_and_identifies_itself() -> None:
    api = Api()
    api.responses = [httpx.Response(200, json=fixture("releases.json"))]
    gateway = api.gateway()
    assert (gateway.via, len(gateway.releases("o/r"))) == ("token", 2)
    request = api.requests[0]
    assert str(request.url) == "https://api.github.com/repos/o/r/releases?per_page=15"
    assert request.headers["authorization"] == "Bearer tok"
    assert request.headers["user-agent"] == USER_AGENT
    assert request.headers["x-github-api-version"] == "2022-11-28"


def test_rest_uses_conditional_requests() -> None:
    api = Api()
    api.responses = [
        httpx.Response(200, json=fixture("advisories.json"), headers={"etag": '"abc"'}),
        httpx.Response(304),
    ]
    gateway = api.gateway()
    first = gateway.advisories("o/r")
    assert gateway.advisories("o/r") == first
    assert "if-none-match" not in api.requests[0].headers
    assert api.requests[1].headers["if-none-match"] == '"abc"'


def test_rest_names_the_rate_limit() -> None:
    api = Api()
    api.responses = [
        httpx.Response(403, headers={"x-ratelimit-remaining": "0", "x-ratelimit-reset": "1761300000"})
    ]
    with pytest.raises(GitHubError, match="rate limit reached, it resets at 1761300000"):
        api.gateway().releases("o/r")


def test_rest_rate_limit_without_a_reset_time() -> None:
    api = Api()
    api.responses = [httpx.Response(429, headers={"x-ratelimit-remaining": "0"})]
    with pytest.raises(GitHubError, match="an unknown time"):
        api.gateway().releases("o/r")


def test_rest_refusals_say_what_github_said() -> None:
    api = Api()
    api.responses = [
        httpx.Response(404, json={"message": "Not Found"}),
        httpx.Response(500, text="boom"),
        httpx.Response(403, json={"message": "forbidden"}),
    ]
    gateway = api.gateway()
    with pytest.raises(GitHubError, match="404 Not Found"):
        gateway.releases("o/r")
    with pytest.raises(GitHubError, match="500 refused"):
        gateway.releases("o/r")
    with pytest.raises(GitHubError, match="403 forbidden"):
        gateway.dependabot_alerts("o/r")


def test_rest_network_failure() -> None:
    def refuse(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("no route", request=request)

    gateway = RestGateway(httpx.Client(transport=httpx.MockTransport(refuse)), "tok")
    with pytest.raises(GitHubError, match="no route"):
        gateway.releases("o/r")


def test_an_unavailable_gateway_says_how_to_fix_it() -> None:
    gateway = UnavailableGateway()
    assert gateway.via == "unavailable"
    for read in (gateway.releases, gateway.advisories, gateway.dependabot_alerts):
        with pytest.raises(GitHubError, match="gh auth login"):
            read("o/r")
    assert "LOOKOUT_GITHUB_TOKEN" in REASON


# --- choosing how to reach GitHub -------------------------------------------------------------------------


def client() -> httpx.Client:
    return httpx.Client()


@pytest.mark.parametrize(
    ("via", "logged_in", "environ", "expected"),
    [
        ("auto", True, {}, "gh"),
        ("auto", True, {"LOOKOUT_GITHUB_TOKEN": "t"}, "gh"),
        ("auto", False, {"LOOKOUT_GITHUB_TOKEN": "t"}, "token"),
        ("auto", False, {"GITHUB_TOKEN": "t"}, "token"),
        ("auto", False, {}, "unavailable"),
        ("token", True, {"GITHUB_TOKEN": "t"}, "token"),
        ("token", True, {}, "unavailable"),
        ("gh", False, {"GITHUB_TOKEN": "t"}, "unavailable"),
        ("gh", True, {}, "gh"),
    ],
)
def test_the_way_to_reach_github(via: str, logged_in: bool, environ: dict[str, str], expected: str) -> None:
    assert choose_gateway(via, client(), environ, logged_in=lambda: logged_in).via == expected


# --- the fetcher ------------------------------------------------------------------------------------------


def fetcher(
    kinds: tuple[str, ...] = ("releases", "advisories", "dependabot"), gateway: object | None = None
) -> GitHubFetcher:
    return GitHubFetcher("gh-watch", ("o/r",), kinds, gateway or FakeGitHub())  # type: ignore[arg-type]


def test_releases_become_items_with_pre_releases_marked() -> None:
    first, second = fetcher(("releases",)).fetch()
    assert (first.title, first.body, first.url) == (
        "o/r Release 2.1.0",
        "Fixes and a faster parser.",
        "https://github.com/o/r/releases/tag/v2.1.0",
    )
    assert second.title == "o/r v2.2.0-rc1 (pre-release)"
    assert first.advisory is None


def test_advisories_carry_structured_facts_for_the_rules() -> None:
    critical, odd = fetcher(("advisories",)).fetch()
    assert (
        critical.title
        == "Security advisory in o/r: SQL injection in JSON lookups (GHSA-aaaa-bbbb-cccc, CVE-2026-1234)"
    )
    assert critical.advisory is not None
    assert (critical.advisory.severity, critical.advisory.package, critical.advisory.ecosystem) == (
        Severity.CRITICAL,
        "Django",
        "pip",
    )
    assert (critical.advisory.identifiers, critical.advisory.watched) == (
        ("GHSA-aaaa-bbbb-cccc", "CVE-2026-1234"),
        True,
    )
    assert "Affected: Django (pip) < 5.2.9, fixed in 5.2.9" in critical.body
    assert odd.advisory is None
    assert odd.title == "Security advisory in o/r: Odd severity, no package (GHSA-dddd-eeee-ffff)"


def test_dependabot_alerts_become_watched_advisories() -> None:
    (alert,) = fetcher(("dependabot",)).fetch()
    assert alert.title.startswith("Dependabot alert in o/r: PKCS12 parsing flaw")
    assert alert.advisory is not None
    assert (alert.advisory.severity, alert.advisory.package, alert.advisory.watched) == (
        Severity.HIGH,
        "cryptography",
        True,
    )


def test_a_failing_read_names_the_repository_and_the_kind() -> None:
    broken = FakeGitHub(error=GitHubError("Resource not accessible"))
    with pytest.raises(SourceError, match="o/r dependabot: Resource not accessible"):
        fetcher(("dependabot",), broken).fetch()
    assert fetcher().name == "gh-watch"
