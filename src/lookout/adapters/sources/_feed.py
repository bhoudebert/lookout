# pyright: basic
"""The one place that touches ``feedparser``, which ships no type stubs."""

from dataclasses import dataclass
from typing import Any

import feedparser


@dataclass(frozen=True, slots=True)
class ParsedFeed:
    """Entries as plain dicts, and the parser's complaint when it found none."""

    entries: list[dict[str, Any]]
    problem: str | None


def parse_feed(content: bytes) -> ParsedFeed:
    """Parse RSS or Atom bytes."""
    parsed = feedparser.parse(content)
    entries: list[dict[str, Any]] = list(parsed.entries)
    problem: str | None = None
    if not entries:
        if parsed.bozo:
            problem = str(parsed.bozo_exception)
        elif not parsed.get("version"):
            problem = "no feed found in the page"
    return ParsedFeed(entries, problem)
