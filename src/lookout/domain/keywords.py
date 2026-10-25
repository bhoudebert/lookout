"""Keeping only the entries a source's keywords ask for (openspec: source-ingestion).

A keyword is a word or a phrase, matched as whole words, ignoring case, accents and markup: ``moto`` finds
"Moto" and "moto-cross" but not "Motorola" or "automotive". A trailing ``*`` lets the word run on: ``moto*``
finds "motos", "motorcycle" and "Motorola". A keyword starting with ``-`` excludes: ``-motorola`` drops any
entry that mentions it. An entry is kept when it has at least one plain keyword (or there are none) and
none of the excluded ones.
"""

import re
import unicodedata
from collections.abc import Sequence
from functools import lru_cache

from lookout.domain.raw import RawItem
from lookout.domain.text import clean_text

_READ_CHARS = 20_000
"""How much of an entry is read for keywords: its markup is stripped first, so long pages are cut."""


def fold(text: str) -> str:
    """Lower case, without accents: "Vélo" and "velo" are the same word."""
    decomposed = unicodedata.normalize("NFKD", text.casefold())
    return "".join(c for c in decomposed if not unicodedata.combining(c))


@lru_cache(maxsize=512)
def _pattern(keyword: str) -> re.Pattern[str]:
    tokens = [
        re.escape(t[:-1]) + r"\w*" if t.endswith("*") and len(t) > 1 else re.escape(t.replace("*", ""))
        for t in fold(keyword).split()
    ]
    return re.compile(r"(?<!\w)" + r"[\W_]+".join(tokens) + r"(?!\w)")


def matches(text: str, keywords: Sequence[str]) -> bool:
    """Whether ``text`` passes the keywords (all of them are read as described above)."""
    wanted = [k.strip() for k in keywords if k.strip() and not k.strip().startswith("-")]
    unwanted = [
        k.strip()[1:].strip() for k in keywords if k.strip().startswith("-") and k.strip()[1:].strip()
    ]
    folded = fold(text)
    if any(_pattern(k).search(folded) for k in unwanted):
        return False
    return not wanted or any(_pattern(k).search(folded) for k in wanted)


def wanted(raw: RawItem, keywords: Sequence[str]) -> bool:
    """Whether an entry passes the keywords, reading its title and its text without the markup."""
    if not keywords:
        return True
    return matches(clean_text(f"{raw.title}\n{raw.body}", _READ_CHARS), keywords)
