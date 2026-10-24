"""The gateway of an installation that can reach GitHub neither through ``gh`` nor with a token."""

from lookout.application.github import GitHubError, Release, SecurityAdvisory

REASON = "GitHub is not reachable: log in with `gh auth login` or set LOOKOUT_GITHUB_TOKEN"


class UnavailableGateway:
    """Fails every read with the reason, so GitHub sources fail alone and `doctor` can say why."""

    def __init__(self, reason: str = REASON) -> None:
        self._reason = reason

    @property
    def via(self) -> str:
        return "unavailable"

    def releases(self, repo: str) -> tuple[Release, ...]:
        raise GitHubError(self._reason)

    def advisories(self, repo: str) -> tuple[SecurityAdvisory, ...]:
        raise GitHubError(self._reason)

    def dependabot_alerts(self, repo: str) -> tuple[SecurityAdvisory, ...]:
        raise GitHubError(self._reason)
