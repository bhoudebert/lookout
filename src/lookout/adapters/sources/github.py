"""Releases, security advisories and Dependabot alerts of declared repositories (openspec: github-sources)."""

from lookout.application.github import GitHubError, GitHubGateway, Release, SecurityAdvisory
from lookout.application.ports_sources import SourceError
from lookout.domain.advisory import Advisory
from lookout.domain.raw import RawItem
from lookout.domain.severity import Severity

KINDS = ("releases", "advisories", "dependabot")


class GitHubFetcher:
    """One source covering several repositories."""

    def __init__(
        self, name: str, repos: tuple[str, ...], kinds: tuple[str, ...], gateway: GitHubGateway
    ) -> None:
        self._name = name
        self._repos = repos
        self._kinds = kinds
        self._gateway = gateway

    @property
    def name(self) -> str:
        return self._name

    def fetch(self) -> tuple[RawItem, ...]:
        """Every wanted kind of every repository; the first read that fails fails the source, naming where."""
        raws: list[RawItem] = []
        for repo in self._repos:
            for kind in self._kinds:
                try:
                    raws.extend(self._read(repo, kind))
                except GitHubError as error:
                    msg = f"{repo} {kind}: {error}"
                    raise SourceError(msg) from error
        return tuple(raws)

    def _read(self, repo: str, kind: str) -> list[RawItem]:
        if kind == "releases":
            return [self._release(repo, r) for r in self._gateway.releases(repo)]
        if kind == "advisories":
            return [self._advisory(repo, a, "Security advisory") for a in self._gateway.advisories(repo)]
        return [self._advisory(repo, a, "Dependabot alert") for a in self._gateway.dependabot_alerts(repo)]

    def _release(self, repo: str, release: Release) -> RawItem:
        label = " (pre-release)" if release.prerelease else ""
        return RawItem(
            source=self._name,
            url=release.url,
            title=f"{repo} {release.name}{label}",
            body=release.notes,
            published_at=release.published_at,
        )

    def _advisory(self, repo: str, advisory: SecurityAdvisory, what: str) -> RawItem:
        ids = tuple(i for i in (advisory.identifier, advisory.cve) if i)
        affected = advisory.vulnerabilities[0] if advisory.vulnerabilities else None
        severity = Severity.parse(advisory.severity)
        structured = (
            Advisory(severity, affected.package, affected.ecosystem.lower(), identifiers=ids, watched=True)
            if severity is not None and affected is not None and affected.package
            else None
        )
        lines = [advisory.description.strip()]
        for v in advisory.vulnerabilities:
            fixed = f", fixed in {v.patched}" if v.patched else ""
            lines.append(f"Affected: {v.package} ({v.ecosystem}) {v.vulnerable}{fixed}")
        label = f" ({', '.join(ids)})" if ids else ""
        return RawItem(
            source=self._name,
            url=advisory.url,
            title=f"{what} in {repo}: {advisory.summary}{label}",
            body="\n".join(line for line in lines if line),
            published_at=advisory.published_at,
            advisory=structured,
        )
