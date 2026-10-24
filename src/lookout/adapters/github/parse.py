"""GitHub's JSON, read defensively: it is outside input like any other (ADR 0002)."""

from datetime import datetime
from typing import Any, cast

from lookout.application.github import GitHubError, Release, SecurityAdvisory, Vulnerability


def _text(data: dict[str, Any], key: str) -> str:
    value = data.get(key)
    return value if isinstance(value, str) else ""


def _moment(value: object) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def _objects(payload: object, what: str) -> list[dict[str, Any]]:
    if not isinstance(payload, list):
        msg = f"GitHub answered {what} with something that is not a list"
        raise GitHubError(msg)
    return [
        cast("dict[str, Any]", entry) for entry in cast("list[object]", payload) if isinstance(entry, dict)
    ]


def releases(payload: object) -> tuple[Release, ...]:
    """Published releases; drafts are skipped."""
    found: list[Release] = []
    for entry in _objects(payload, "the releases"):
        if entry.get("draft") is True or not _text(entry, "html_url"):
            continue
        tag = _text(entry, "tag_name")
        found.append(
            Release(
                tag=tag,
                name=_text(entry, "name") or tag,
                notes=_text(entry, "body"),
                url=_text(entry, "html_url"),
                published_at=_moment(entry.get("published_at")),
                prerelease=entry.get("prerelease") is True,
            )
        )
    return tuple(found)


def _vulnerability(entry: dict[str, Any]) -> Vulnerability | None:
    package = entry.get("package")
    if not isinstance(package, dict):
        return None
    package_data = cast("dict[str, Any]", package)
    patched = entry.get("patched_versions") or entry.get("first_patched_version")
    if isinstance(patched, dict):
        patched = cast("dict[str, Any]", patched).get("identifier")
    return Vulnerability(
        ecosystem=_text(package_data, "ecosystem"),
        package=_text(package_data, "name"),
        vulnerable=_text(entry, "vulnerable_version_range"),
        patched=patched if isinstance(patched, str) else "",
    )


def _vulnerabilities(entry: dict[str, Any]) -> tuple[Vulnerability, ...]:
    raw = entry.get("vulnerabilities")
    if not isinstance(raw, list):
        return ()
    found = (
        _vulnerability(cast("dict[str, Any]", v)) for v in cast("list[object]", raw) if isinstance(v, dict)
    )
    return tuple(v for v in found if v is not None)


def advisories(payload: object) -> tuple[SecurityAdvisory, ...]:
    """Published repository security advisories."""
    found: list[SecurityAdvisory] = []
    for entry in _objects(payload, "the advisories"):
        if not _text(entry, "html_url"):
            continue
        found.append(
            SecurityAdvisory(
                identifier=_text(entry, "ghsa_id"),
                cve=_text(entry, "cve_id") or None,
                summary=_text(entry, "summary"),
                description=_text(entry, "description"),
                severity=_text(entry, "severity"),
                url=_text(entry, "html_url"),
                published_at=_moment(entry.get("published_at")),
                vulnerabilities=_vulnerabilities(entry),
            )
        )
    return tuple(found)


def dependabot_alerts(payload: object) -> tuple[SecurityAdvisory, ...]:
    """Open Dependabot alerts of a repository."""
    found: list[SecurityAdvisory] = []
    for entry in _objects(payload, "the Dependabot alerts"):
        advisory = entry.get("security_advisory")
        vulnerability = entry.get("security_vulnerability")
        if not isinstance(advisory, dict) or not _text(entry, "html_url"):
            continue
        advisory_data = cast("dict[str, Any]", advisory)
        affected = (
            (_vulnerability(cast("dict[str, Any]", vulnerability)),)
            if isinstance(vulnerability, dict)
            else ()
        )
        found.append(
            SecurityAdvisory(
                identifier=_text(advisory_data, "ghsa_id"),
                cve=_text(advisory_data, "cve_id") or None,
                summary=_text(advisory_data, "summary"),
                description=_text(advisory_data, "description"),
                severity=_text(advisory_data, "severity"),
                url=_text(entry, "html_url"),
                published_at=_moment(entry.get("created_at")),
                vulnerabilities=tuple(v for v in affected if v is not None),
            )
        )
    return tuple(found)
