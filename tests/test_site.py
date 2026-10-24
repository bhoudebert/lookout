"""The website: every local link and image exists, every image has text for those who cannot see it."""

from html.parser import HTMLParser
from pathlib import Path

SITE = Path(__file__).parent.parent / "site"


class _Links(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.local: list[str] = []
        self.images_without_alt: list[str] = []
        self.title = ""
        self._in_title = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        found = dict(attrs)
        if tag == "title":
            self._in_title = True
        if tag == "img":
            src = found.get("src") or ""
            self.local.append(src)
            if not found.get("alt"):
                self.images_without_alt.append(src)
        href = found.get("href") or ""
        if tag == "a" and href and not href.startswith(("http", "#", "mailto:")):
            self.local.append(href)

    def handle_endtag(self, tag: str) -> None:
        if tag == "title":
            self._in_title = False

    def handle_data(self, data: str) -> None:
        if self._in_title:
            self.title += data


def _page() -> _Links:
    parser = _Links()
    parser.feed((SITE / "index.html").read_text())
    return parser


def test_every_image_is_there_and_described() -> None:
    page = _page()
    assert page.images_without_alt == []
    images = [s for s in page.local if s.startswith("shots/")]
    assert images
    assert all((SITE / s).is_file() for s in images)


def test_links_into_the_guide_name_pages_that_exist() -> None:
    guide = SITE.parent / "docs" / "guide"
    page = _page()
    targets = [s.removeprefix("guide/").rstrip("/") for s in page.local if s.startswith("guide/")]
    assert targets
    for target in targets:
        name = target or "index"
        assert (guide / f"{name}.md").is_file(), f"the site links to guide/{target}, which has no page"


def test_the_page_has_a_title() -> None:
    assert _page().title.startswith("Lookout")
