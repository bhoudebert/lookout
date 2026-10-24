"""What Lookout needs from GitHub, however it is reached (ADR 0006): the local ``gh`` login or a token."""

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol


class GitHubError(Exception):
    """GitHub could not be read: no access, no network, rate limited."""


@dataclass(frozen=True, slots=True)
class Release:
    """A published release of a repository."""

    tag: str
    name: str
    notes: str
    url: str
    published_at: datetime | None
    prerelease: bool


@dataclass(frozen=True, slots=True)
class Vulnerability:
    """One affected package of an advisory, with the ranges as GitHub writes them."""

    ecosystem: str
    package: str
    vulnerable: str
    patched: str


@dataclass(frozen=True, slots=True)
class SecurityAdvisory:
    """A security advisory or a Dependabot alert."""

    identifier: str
    cve: str | None
    summary: str
    description: str
    severity: str
    url: str
    published_at: datetime | None
    vulnerabilities: tuple[Vulnerability, ...]


class GitHubGateway(Protocol):
    """Reads one repository."""

    @property
    def via(self) -> str:
        """How GitHub is reached: ``gh``, ``token`` or ``unavailable``."""
        ...

    def releases(self, repo: str) -> tuple[Release, ...]: ...

    def advisories(self, repo: str) -> tuple[SecurityAdvisory, ...]: ...

    def dependabot_alerts(self, repo: str) -> tuple[SecurityAdvisory, ...]: ...
