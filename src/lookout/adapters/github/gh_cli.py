"""GitHub through the local ``gh`` executable, which reuses the user's login: no token stored (ADR 0006)."""

import json
import subprocess

from lookout.adapters.github.base import ApiGateway
from lookout.application.github import GitHubError


def gh_is_logged_in(executable: str = "gh") -> bool:
    """True when ``gh`` exists and has a login."""
    try:
        done = subprocess.run([executable, "auth", "status"], capture_output=True, timeout=15, check=False)  # noqa: S603
    except (OSError, subprocess.TimeoutExpired):
        return False
    return done.returncode == 0


class GhCliGateway(ApiGateway):
    """Runs ``gh api <path>``."""

    def __init__(self, executable: str = "gh", timeout: float = 30.0) -> None:
        self._executable = executable
        self._timeout = timeout

    @property
    def via(self) -> str:
        return "gh"

    def _get(self, path: str) -> object:
        command = [self._executable, "api", path, "-H", "Accept: application/vnd.github+json"]
        try:
            done = subprocess.run(command, capture_output=True, text=True, timeout=self._timeout, check=False)  # noqa: S603
        except (OSError, subprocess.TimeoutExpired) as error:
            msg = f"gh api {path}: {error}"
            raise GitHubError(msg) from error
        if done.returncode != 0:
            msg = f"gh api {path}: {done.stderr.strip() or 'failed'}"
            raise GitHubError(msg)
        try:
            return json.loads(done.stdout)
        except json.JSONDecodeError as error:
            msg = f"gh api {path}: the answer is not JSON"
            raise GitHubError(msg) from error
