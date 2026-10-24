"""A fake GitHub for the scenario tests."""

import json
import os
import stat
from pathlib import Path

from lookout.adapters.github import parse
from lookout.application.github import Release, SecurityAdvisory

FIXTURES = Path(__file__).parent / "fixtures" / "github"

FAKE_GH = """#!/bin/sh
# A stand-in for the gh executable: `gh auth status`, and `gh api PATH` answered from fixture files.
if [ "$1" = "auth" ]; then exit "${FAKE_GH_AUTH:-0}"; fi
[ -n "$FAKE_GH_SLEEP" ] && sleep "$FAKE_GH_SLEEP"
case "$2" in
  */garbage/*) echo "not json" ;;
  */missing/*) echo "gh: Not Found (HTTP 404)" >&2; exit 1 ;;
  */releases*) cat "$FAKE_GH_DIR/releases.json" ;;
  */security-advisories*) cat "$FAKE_GH_DIR/advisories.json" ;;
  */dependabot/alerts*)
    if [ -n "$FAKE_GH_DENY_DEPENDABOT" ]; then echo "gh: Resource not accessible (HTTP 403)" >&2; exit 1; fi
    cat "$FAKE_GH_DIR/dependabot.json" ;;
  *) echo "gh: Not Found (HTTP 404)" >&2; exit 1 ;;
esac
"""


def install_fake_gh(directory: Path) -> str:
    """Write the fake executable and point it at the fixtures; returns its path."""
    path = directory / "gh"
    path.write_text(FAKE_GH)
    path.chmod(path.stat().st_mode | stat.S_IEXEC)
    os.environ["FAKE_GH_DIR"] = str(FIXTURES)
    return str(path)


def fixture(name: str) -> object:
    return json.loads((FIXTURES / name).read_text())


class FakeGitHub:
    """The port, answering from the fixtures, or failing as asked."""

    def __init__(self, via: str = "gh", error: Exception | None = None) -> None:
        self.via = via
        self.error = error

    def releases(self, repo: str) -> tuple[Release, ...]:
        if self.error:
            raise self.error
        return parse.releases(fixture("releases.json"))

    def advisories(self, repo: str) -> tuple[SecurityAdvisory, ...]:
        if self.error:
            raise self.error
        return parse.advisories(fixture("advisories.json"))

    def dependabot_alerts(self, repo: str) -> tuple[SecurityAdvisory, ...]:
        if self.error:
            raise self.error
        return parse.dependabot_alerts(fixture("dependabot.json"))
