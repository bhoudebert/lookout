"""Vulnerabilities of the declared stack from OSV, flagged when CISA lists them as exploited."""

from collections.abc import Callable
from datetime import datetime, timedelta
from typing import Any, cast

import httpx

from lookout.adapters.sources.rss import USER_AGENT
from lookout.application.ports_sources import SourceError
from lookout.domain.advisory import Advisory
from lookout.domain.cvss import severity_of
from lookout.domain.raw import RawItem
from lookout.domain.severity import Severity
from lookout.domain.stack import StackEntry

OSV_QUERY = "https://api.osv.dev/v1/query"
KEV_URL = "https://www.cisa.gov/sites/default/files/feeds/known_exploited_vulnerabilities.json"
ECOSYSTEMS = {"pypi": "PyPI", "npm": "npm", "crates": "crates.io", "go": "Go"}
MAX_PAGES = 10
SUMMARY_CHARS = 200


class OsvFetcher:
    """One source covering every stack entry OSV knows an ecosystem for."""

    def __init__(
        self,
        name: str,
        entries: tuple[StackEntry, ...],
        client: httpx.Client,
        now: Callable[[], datetime],
        *,
        kev: bool = True,
        since_days: int = 30,
    ) -> None:
        self._name = name
        self._entries = tuple(e for e in entries if e.ecosystem in ECOSYSTEMS)
        self._client = client
        self._now = now
        self._kev = kev
        self._since = timedelta(days=since_days)

    @property
    def name(self) -> str:
        return self._name

    def fetch(self) -> tuple[RawItem, ...]:
        """Recent vulnerabilities of every queryable stack entry."""
        if not self._entries:
            covered = ", ".join(ECOSYSTEMS)
            msg = f"no stack entry has an ecosystem OSV covers ({covered}): declare one under `stack`"
            raise SourceError(msg)
        exploited = self._exploited() if self._kev else frozenset[str]()
        cutoff = self._now() - self._since
        raws = [
            raw
            for entry in self._entries
            for vuln in self._vulnerabilities(entry)
            if (raw := self._raw(entry, vuln, exploited, cutoff)) is not None
        ]
        return tuple(raws)

    # Network ----------------------------------------------------------------------------------------------

    def _vulnerabilities(self, entry: StackEntry) -> list[dict[str, Any]]:
        query: dict[str, Any] = {"package": {"name": entry.name, "ecosystem": ECOSYSTEMS[entry.ecosystem]}}
        if entry.version:
            query["version"] = entry.version
        found: list[dict[str, Any]] = []
        for _ in range(MAX_PAGES):
            body = self._call("POST", OSV_QUERY, f"OSV query for {entry.name}", json=query)
            vulns = body.get("vulns")
            if isinstance(vulns, list):
                found.extend(
                    cast("dict[str, Any]", v) for v in cast("list[object]", vulns) if isinstance(v, dict)
                )
            token = body.get("next_page_token")
            if not isinstance(token, str) or not token:
                break
            query = {**query, "page_token": token}
        return found

    def _exploited(self) -> frozenset[str]:
        body = self._call("GET", KEV_URL, "the CISA catalogue of exploited vulnerabilities")
        entries = body.get("vulnerabilities", [])
        if not isinstance(entries, list):
            return frozenset()
        return frozenset(
            str(cast("dict[str, Any]", e).get("cveID"))
            for e in cast("list[object]", entries)
            if isinstance(e, dict)
        )

    def _call(self, method: str, url: str, what: str, **options: Any) -> dict[str, Any]:  # noqa: ANN401
        try:
            response = self._client.request(method, url, headers={"User-Agent": USER_AGENT}, **options)
            response.raise_for_status()
            body = response.json()
        except (httpx.HTTPError, ValueError) as error:
            msg = f"{what}: {error}"
            raise SourceError(msg) from error
        if not isinstance(body, dict):
            msg = f"{what}: the answer is not a JSON object"
            raise SourceError(msg)
        return cast("dict[str, Any]", body)

    # Reading ----------------------------------------------------------------------------------------------

    def _raw(
        self, entry: StackEntry, vuln: dict[str, Any], exploited: frozenset[str], cutoff: datetime
    ) -> RawItem | None:
        vuln_id = vuln.get("id")
        if not isinstance(vuln_id, str) or not vuln_id:
            return None
        published = _moment(vuln.get("published")) or _moment(vuln.get("modified"))
        if published is not None and published < cutoff:
            return None
        aliases = tuple(a for a in cast("list[object]", vuln.get("aliases") or []) if isinstance(a, str))
        identifiers = (vuln_id, *(a for a in aliases if a.startswith(("CVE-", "GHSA-")) and a != vuln_id))
        summary = _summary(vuln)
        advisory = Advisory(
            severity=_severity(vuln),
            package=entry.name,
            ecosystem=entry.ecosystem,
            known_exploited=any(a in exploited for a in aliases),
            identifiers=identifiers,
        )
        return RawItem(
            source=self._name,
            url=f"https://osv.dev/vulnerability/{vuln_id}",
            title=f"{vuln_id}: {summary[:SUMMARY_CHARS] or 'vulnerability'} ({entry.name})",
            body=_text(vuln),
            published_at=published,
            advisory=advisory,
        )


def _summary(vuln: dict[str, Any]) -> str:
    summary = vuln.get("summary")
    if isinstance(summary, str) and summary.strip():
        return summary.strip()
    lines = str(vuln.get("details") or "").strip().splitlines()
    return lines[0] if lines else ""


def _moment(value: object) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def _severity(vuln: dict[str, Any]) -> Severity:
    database = vuln.get("database_specific")
    if isinstance(database, dict):
        word = Severity.parse(str(cast("dict[str, Any]", database).get("severity") or ""))
        if word is not None:
            return word
    scores = vuln.get("severity")
    for entry in cast("list[object]", scores) if isinstance(scores, list) else []:
        if isinstance(entry, dict):
            vector = cast("dict[str, Any]", entry).get("score")
            found = severity_of(vector) if isinstance(vector, str) else None
            if found is not None:
                return found
    return Severity.MODERATE


def _text(vuln: dict[str, Any]) -> str:
    lines = [str(vuln.get("details") or "").strip()]
    fixed: list[str] = []
    for affected in cast("list[object]", vuln.get("affected") or []):
        if not isinstance(affected, dict):
            continue
        for rng in cast("list[object]", cast("dict[str, Any]", affected).get("ranges") or []):
            if isinstance(rng, dict):
                for event in cast("list[object]", cast("dict[str, Any]", rng).get("events") or []):
                    if isinstance(event, dict) and isinstance(
                        cast("dict[str, Any]", event).get("fixed"), str
                    ):
                        fixed.append(cast("str", cast("dict[str, Any]", event)["fixed"]))
    if fixed:
        lines.append(f"Fixed in {', '.join(sorted(set(fixed)))}")
    return "\n".join(line for line in lines if line)
