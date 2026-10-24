"""Cleaning of text fetched from the outside: it is data, never instructions (ADR 0002)."""

import re
import unicodedata
from html.parser import HTMLParser

_SPACES = re.compile(r"[ \t\r\f\v]+")
_BLANKS = re.compile(r"\n{3,}")
_SKIPPED = frozenset({"script", "style", "template"})


class _Text(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self._skip = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in _SKIPPED:
            self._skip += 1
        elif tag in ("br", "p", "div", "li", "tr", "h1", "h2", "h3"):
            self.parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag in _SKIPPED and self._skip:
            self._skip -= 1

    def handle_data(self, data: str) -> None:
        if not self._skip:
            self.parts.append(data)


def clean_text(markup: str, limit: int) -> str:
    """Strip markup, drop control characters, collapse blanks and cut at ``limit`` characters."""
    parser = _Text()
    parser.feed(markup)
    parser.close()
    text = "".join(parser.parts)
    text = "".join(c for c in text if c in "\n" or unicodedata.category(c)[0] != "C")
    text = _BLANKS.sub("\n\n", _SPACES.sub(" ", text)).strip()
    return text if len(text) <= limit else text[: limit - 1].rstrip() + "…"
