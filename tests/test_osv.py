"""Scenarios of openspec/specs/osv-advisories."""

import json
from datetime import UTC, datetime
from pathlib import Path

import httpx
import pytest
import yaml
from tests.cli_support import Lookout, reading
from tests.support import NOW

from lookout.adapters.sources.osv import KEV_URL, MAX_PAGES, OSV_QUERY, OsvFetcher
from lookout.application.errors import ConfigError
from lookout.application.ports_sources import SourceError
from lookout.bootstrap.container import build, load
from lookout.domain.priority import Priority
from lookout.domain.severity import Severity
from lookout.domain.stack import StackEntry

FIXTURES = Path(__file__).parent / "fixtures" / "osv"
DJANGO = StackEntry("django", "pypi", version="5.1.0")


def fixture(name: str) -> bytes:
    return (FIXTURES / name).read_bytes()


class Osv:
    """OSV and CISA, scripted: pages of vulnerabilities per package name."""

    def __init__(self, **pages: list[bytes]) -> None:
        self.pages = pages
        self.queries: list[dict[str, object]] = []
        self.kev: httpx.Response = httpx.Response(200, content=fixture("kev.json"))

    def __call__(self, request: httpx.Request) -> httpx.Response:
        if str(request.url) == KEV_URL:
            return self.kev
        assert str(request.url) == OSV_QUERY
        query = json.loads(request.content)
        self.queries.append(query)
        queue = self.pages.get(query["package"]["name"], [])
        return httpx.Response(200, content=queue.pop(0) if queue else b'{"vulns": []}')

    def fetcher(self, entries: tuple[StackEntry, ...] = (DJANGO,), **kw: object) -> OsvFetcher:
        client = httpx.Client(transport=httpx.MockTransport(self))
        return OsvFetcher("osv", entries, client, lambda: NOW, **kw)  # type: ignore[arg-type]


def django_pages() -> Osv:
    return Osv(django=[fixture("django-page1.json"), fixture("django-page2.json")])


def test_recent_vulnerabilities_become_items_with_facts_for_the_rules() -> None:
    osv = django_pages()
    raws = {r.url.rsplit("/", 1)[1]: r for r in osv.fetcher().fetch()}
    assert set(raws) == {
        "GHSA-aaaa-bbbb-cccc",
        "PYSEC-2026-77",
        "GHSA-low-vector",
        "GHSA-nodate",
        "GHSA-bad-date",
    }

    critical = raws["GHSA-aaaa-bbbb-cccc"]
    assert critical.title == "GHSA-aaaa-bbbb-cccc: SQL injection in JSON key lookups (django)"
    assert critical.advisory is not None
    assert (critical.advisory.severity, critical.advisory.package, critical.advisory.ecosystem) == (
        Severity.CRITICAL,
        "django",
        "pypi",
    )
    assert critical.advisory.identifiers == ("GHSA-aaaa-bbbb-cccc", "CVE-2026-1234")
    assert (critical.advisory.known_exploited, critical.advisory.watched) == (False, False)
    assert critical.published_at == datetime(2026, 10, 20, 8, tzinfo=UTC)
    assert "Fixed in 5.1.2, 5.2.9" in critical.body
    assert "A crafted key allows SQL injection." in critical.body


def test_severity_comes_from_the_database_then_the_vector_then_moderate() -> None:
    raws = {r.url.rsplit("/", 1)[1]: r for r in django_pages().fetcher().fetch()}
    severities = {key: raw.advisory.severity for key, raw in raws.items() if raw.advisory}
    assert severities["GHSA-aaaa-bbbb-cccc"] is Severity.CRITICAL  # database_specific
    assert severities["PYSEC-2026-77"] is Severity.CRITICAL  # computed from CVSS:3.1 9.8
    assert severities["GHSA-low-vector"] is Severity.MODERATE  # nothing usable
    assert severities["GHSA-nodate"] is Severity.MODERATE


def test_only_recent_vulnerabilities_are_kept_and_old_history_is_dropped() -> None:
    urls = [r.url for r in django_pages().fetcher().fetch()]
    assert "https://osv.dev/vulnerability/OSV-OLD-1" not in urls
    wide = [r.url for r in django_pages().fetcher(since_days=700).fetch()]
    assert "https://osv.dev/vulnerability/OSV-OLD-1" in wide


def test_a_summary_falls_back_to_the_first_line_of_the_details() -> None:
    raws = {r.url.rsplit("/", 1)[1]: r for r in django_pages().fetcher().fetch()}
    assert raws["PYSEC-2026-77"].title == "PYSEC-2026-77: Only details here, no summary. (django)"
    assert raws["GHSA-nodate"].published_at is None
    assert raws["GHSA-bad-date"].title == "GHSA-bad-date: Unreadable date (django)"


def test_the_declared_version_is_sent_to_osv_and_pages_are_followed() -> None:
    osv = django_pages()
    osv.fetcher().fetch()
    assert osv.queries[0] == {"package": {"name": "django", "ecosystem": "PyPI"}, "version": "5.1.0"}
    assert osv.queries[1]["page_token"] == "page-2"  # noqa: S105
    assert len(osv.queries) == 2


def test_pagination_is_bounded() -> None:
    endless = b'{"vulns": [], "next_page_token": "again"}'
    osv = Osv(django=[endless] * 50)
    osv.fetcher(kev=False).fetch()
    assert len(osv.queries) == MAX_PAGES


def test_without_a_version_osv_is_asked_about_the_package() -> None:
    osv = Osv()
    osv.fetcher((StackEntry("react", "npm"),)).fetch()
    assert osv.queries == [{"package": {"name": "react", "ecosystem": "npm"}}]


def test_ecosystems_osv_does_not_cover_are_skipped() -> None:
    osv = Osv()
    entries = (
        StackEntry("postgresql"),
        StackEntry("serde", "crates"),
        StackEntry("gin", "go"),
        StackEntry("x", "github"),
    )
    osv.fetcher(entries).fetch()
    assert [q["package"] for q in osv.queries] == [
        {"name": "serde", "ecosystem": "crates.io"},
        {"name": "gin", "ecosystem": "Go"},
    ]


def test_a_stack_osv_cannot_use_fails_the_source_with_the_fix() -> None:
    with pytest.raises(
        SourceError, match=r"no stack entry has an ecosystem OSV covers \(pypi, npm, crates, go\)"
    ):
        Osv().fetcher((StackEntry("postgresql"),)).fetch()
    with pytest.raises(SourceError, match="declare one under `stack`"):
        Osv().fetcher(()).fetch()


def test_a_cve_listed_by_cisa_is_known_to_be_exploited() -> None:
    raws = {r.url.rsplit("/", 1)[1]: r for r in django_pages().fetcher().fetch()}
    exploited = {key: raw.advisory.known_exploited for key, raw in raws.items() if raw.advisory}
    assert exploited["PYSEC-2026-77"] is True
    assert exploited["GHSA-aaaa-bbbb-cccc"] is False


def test_the_catalogue_can_be_turned_off_and_is_then_not_fetched() -> None:
    osv = django_pages()
    raws = osv.fetcher(kev=False).fetch()
    assert all(not r.advisory.known_exploited for r in raws if r.advisory)
    osv.kev = httpx.Response(500)
    assert django_pages().fetcher(kev=False).fetch()


@pytest.mark.parametrize(
    ("kev", "message"),
    [
        (httpx.Response(503), "CISA catalogue"),
        (httpx.Response(200, content=b"<html>"), "CISA catalogue"),
        (httpx.Response(200, content=b"[1, 2]"), "not a JSON object"),
    ],
)
def test_an_unreadable_catalogue_fails_the_source_naming_it(kev: httpx.Response, message: str) -> None:
    osv = django_pages()
    osv.kev = kev
    with pytest.raises(SourceError, match=message):
        osv.fetcher().fetch()


def test_a_catalogue_without_a_list_marks_nothing() -> None:
    osv = django_pages()
    osv.kev = httpx.Response(200, content=b'{"vulnerabilities": "oops"}')
    assert all(not r.advisory.known_exploited for r in osv.fetcher().fetch() if r.advisory)


def test_osv_failures_name_what_failed() -> None:
    def down(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("no route", request=request)

    fetcher = OsvFetcher(
        "osv", (DJANGO,), httpx.Client(transport=httpx.MockTransport(down)), lambda: NOW, kev=False
    )
    with pytest.raises(SourceError, match="OSV query for django: no route"):
        fetcher.fetch()


def test_osv_answering_with_junk_is_a_source_error() -> None:
    osv = Osv(django=[b"[1]"])
    with pytest.raises(SourceError, match="not a JSON object"):
        osv.fetcher(kev=False).fetch()
    osv = Osv(django=[b'{"vulns": "none"}'])
    assert osv.fetcher(kev=False).fetch() == ()


# --- the rules, end to end ---------------------------------------------------------------------------------


def run_osv(tmp_path: Path, osv: Osv | None = None) -> Lookout:
    lookout = Lookout(
        tmp_path,
        stack=[{"name": "django", "ecosystem": "pypi", "version": "5.1.0"}],
        sources=[{"name": "osv", "type": "osv", "since_days": 30}],
    )
    source = osv or django_pages()
    lookout.network.osv = source
    lookout.network.kev = fixture("kev.json")
    lookout.network.chat = lambda _request: reading(score=5)
    lookout("run")
    return lookout


def test_a_critical_vulnerability_on_a_declared_package_is_p0_and_a_moderate_exploited_one_too(
    tmp_path: Path,
) -> None:
    lookout = run_osv(tmp_path)
    rows = {r.split()[2]: r for r in lookout("inbox", "--limit", "20").splitlines()[:-1]}
    critical = next(r for r in rows.values() if "SQL injection in JSON key" in r)
    assert critical.startswith(Priority.P0.name)
    assert (
        "rule: critical advisory GHSA-aaaa-bbbb-cccc, CVE-2026-1234 affects django, which you use"
        in lookout("explain", critical.split()[2])
    )
    unrated = next(r for r in rows.values() if "Odd severity data" in r)
    assert unrated.startswith("P3")


def test_known_exploited_is_p0_whatever_the_severity(tmp_path: Path) -> None:
    osv = Osv(
        django=[
            json.dumps(
                {
                    "vulns": [
                        {
                            "id": "PYSEC-X",
                            "aliases": ["CVE-2026-5555"],
                            "summary": "Exploited",
                            "published": "2026-10-23T00:00:00Z",
                            "database_specific": {"severity": "LOW"},
                        }
                    ]
                }
            ).encode()
        ]
    )
    lookout = run_osv(tmp_path, osv)
    line = next(r for r in lookout("inbox").splitlines() if "Exploited" in r)
    assert line.startswith("P0")
    assert "known to be exploited" in lookout("explain", line.split()[2])


# --- configuration ------------------------------------------------------------------------------------------


def write(tmp_path: Path, source: dict[str, object]) -> Path:
    path = tmp_path / "lookout.yaml"
    path.write_text(
        yaml.safe_dump(
            {"database": str(tmp_path / "db"), "sources": [{"name": "o", "type": "osv", **source}]}
        )
    )
    return path


@pytest.mark.parametrize(
    ("source", "message"),
    [
        ({"kev": "yes"}, "'kev' must be true or false"),
        ({"since_days": 0}, "'since_days' must be a whole number"),
        ({"since_days": True}, "'since_days'"),
    ],
)
def test_osv_settings_are_validated(tmp_path: Path, source: dict[str, object], message: str) -> None:
    with pytest.raises(ConfigError, match=message):
        build(load(write(tmp_path, source), {}))


def test_stack_versions_are_read_and_must_be_text(tmp_path: Path) -> None:
    good = tmp_path / "good.yaml"
    good.write_text(yaml.safe_dump({"stack": [{"name": "django", "ecosystem": "pypi", "version": "5.1.0"}]}))
    assert load(good, {}).stack.entries[0].version == "5.1.0"
    bad = tmp_path / "bad.yaml"
    bad.write_text("stack:\n  - name: django\n    version: 5.1\n")
    with pytest.raises(ConfigError, match="'version' must be text"):
        load(bad, {})
