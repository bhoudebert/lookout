"""Stack matching, URL canonicalisation, severity parsing: scenarios of stack-watch and source-ingestion."""

import pytest

from lookout.domain.advisory import Advisory
from lookout.domain.severity import Severity
from lookout.domain.stack import Stack, StackEntry
from lookout.domain.urls import canonical_url

STACK = Stack(
    (
        StackEntry("postgresql", "other", aliases=("postgres",)),
        StackEntry("django", "pypi"),
        StackEntry("react", "npm"),
    )
)


def test_alias_matches_in_text() -> None:
    assert STACK.match("Postgres 17 released") == ("postgresql",)


def test_name_must_be_a_whole_word() -> None:
    assert STACK.match("reactive programming and djangoish things") == ()
    assert STACK.match("react-native news") == ()


def test_advisory_package_matches_without_a_mention() -> None:
    advisory = Advisory(Severity.HIGH, "Django", "pypi")
    assert STACK.match("security release", advisory) == ("django",)


def test_several_entries_can_match() -> None:
    assert STACK.match("django and React ship fixes") == ("django", "react")


def test_empty_stack_matches_nothing() -> None:
    assert Stack().match("anything") == ()


def test_same_story_from_two_sources_has_one_canonical_url() -> None:
    a = canonical_url("https://Example.com/post/?utm_source=hn&id=3#top")
    b = canonical_url("https://example.com/post?id=3&fbclid=zzz")
    assert a == b == "https://example.com/post?id=3"


def test_root_path_is_kept() -> None:
    assert canonical_url("https://example.com") == "https://example.com/"


@pytest.mark.parametrize(
    ("word", "expected"),
    [
        ("CRITICAL", Severity.CRITICAL),
        (" medium ", Severity.MODERATE),
        ("moderate", Severity.MODERATE),
        ("high", Severity.HIGH),
        ("low", Severity.LOW),
        ("weird", None),
    ],
)
def test_severity_parsing(word: str, expected: Severity | None) -> None:
    assert Severity.parse(word) is expected
