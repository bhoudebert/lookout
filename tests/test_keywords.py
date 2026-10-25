"""Scenarios of openspec/specs/source-ingestion: keywords."""

import pytest

from lookout.domain.keywords import fold, matches, wanted
from lookout.domain.raw import RawItem


@pytest.mark.parametrize(
    ("text", "keywords", "expected"),
    [
        # whole words, not substrings
        ("Casque moto Scorpion à -30%", ["moto"], True),
        ("Smartphone Motorola Edge", ["moto"], False),
        ("Un développement durable", ["velo"], False),
        ("Pièces automotive", ["moto"], False),
        ("Pneu cross-moto", ["moto"], True),
        ("Moto.", ["moto"], True),
        # case and accents do not matter, either way round
        ("VÉLO électrique Decathlon", ["velo"], True),
        ("velo electrique", ["Vélo"], True),
        ("Café", ["CAFE"], True),
        # a trailing star lets the word run on
        ("Des vélos à moitié prix", ["vélo*"], True),
        ("Des vélos à moitié prix", ["vélo"], False),
        ("Motorola Edge", ["moto*"], True),
        ("Une moto", ["moto*"], True),
        # phrases, whatever separates their words
        ("Vélo électrique pliable", ["vélo électrique"], True),
        ("vélo-électrique", ["vélo électrique"], True),
        ("Vélo ou électrique", ["vélo électrique"], False),
        ("Cartes graphiques RTX", ["carte* graphique*"], True),
        # any one plain keyword is enough, and none at all keeps everything
        ("SSD NVMe 1To", ["ssd", "casque"], True),
        ("Tapis de souris", ["ssd", "casque"], False),
        ("Tapis de souris", [], True),
        # excluded words drop an entry, on their own or with plain keywords
        ("Smartphone Motorola", ["-motorola"], False),
        ("Smartphone Samsung", ["-motorola"], True),
        ("Moto Motorola", ["moto", "-motorola"], False),
        ("Casque moto", ["moto", "-motorola"], True),
        ("Tapis", ["moto", "-motorola"], False),
        # blanks and a lone dash are ignored
        ("Casque moto", ["  moto  ", "", "-", "  "], True),
        ("Rien", ["", "  "], True),
    ],
)
def test_keywords_match_whole_words_ignoring_case_and_accents(
    text: str, keywords: list[str], expected: bool
) -> None:
    assert matches(text, keywords) is expected


def test_folding_removes_accents_and_case() -> None:
    assert fold("Élève ÇA Vélo") == "eleve ca velo"


def entry(title: str, body: str = "") -> RawItem:
    return RawItem("s", "https://x.test/1", title, body)


def test_markup_and_addresses_inside_it_are_not_read() -> None:
    body = (
        '<p>Une souris</p><img src="https://cdn.test/velo-electrique.jpg" alt="velo"><a href="/moto">lien</a>'
    )
    assert not wanted(entry("Souris", body), ["velo", "moto"])
    assert wanted(entry("Souris", "<p>Pour votre <b>vélo</b></p>"), ["velo"])


def test_the_title_counts_and_an_entry_without_keywords_always_passes() -> None:
    assert wanted(entry("Casque moto"), ["moto"])
    assert wanted(entry("Anything"), [])
    assert wanted(entry("Anything"), ())


def test_only_the_start_of_a_very_long_entry_is_read() -> None:
    long = "mot " * 10_000 + "moto"
    assert not wanted(entry("Long", long), ["moto"])
