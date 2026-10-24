"""The three GitHub reads shared by every way of reaching GitHub."""

from abc import ABC, abstractmethod

from lookout.adapters.github import parse
from lookout.application.github import Release, SecurityAdvisory


class ApiGateway(ABC):
    """A gateway that only has to know how to GET a path of the REST API and return its JSON."""

    @property
    @abstractmethod
    def via(self) -> str: ...

    @abstractmethod
    def _get(self, path: str) -> object:
        """The decoded JSON of ``path``, or ``GitHubError``."""

    def releases(self, repo: str) -> tuple[Release, ...]:
        return parse.releases(self._get(f"repos/{repo}/releases?per_page=15"))

    def advisories(self, repo: str) -> tuple[SecurityAdvisory, ...]:
        return parse.advisories(self._get(f"repos/{repo}/security-advisories?state=published&per_page=20"))

    def dependabot_alerts(self, repo: str) -> tuple[SecurityAdvisory, ...]:
        return parse.dependabot_alerts(self._get(f"repos/{repo}/dependabot/alerts?state=open&per_page=50"))
