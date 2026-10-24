"""The stack the user declares, and matching of items to it (openspec: stack-watch)."""

import re
from dataclasses import dataclass

from lookout.domain.advisory import Advisory


@dataclass(frozen=True, slots=True)
class StackEntry:
    """One thing the user depends on."""

    name: str
    ecosystem: str = "other"
    aliases: tuple[str, ...] = ()
    version: str = ""

    @property
    def names(self) -> tuple[str, ...]:
        """The name and its aliases, lower-cased."""
        return tuple(n.lower() for n in (self.name, *self.aliases))


@dataclass(frozen=True, slots=True)
class Stack:
    """The declared entries."""

    entries: tuple[StackEntry, ...] = ()

    def match(self, text: str, advisory: Advisory | None = None) -> tuple[str, ...]:
        """Names of entries an item concerns: its advisory package, or a whole-word mention in its text."""
        return tuple(entry.name for entry in self.entries if _concerns(entry, text, advisory))


def _concerns(entry: StackEntry, text: str, advisory: Advisory | None) -> bool:
    if advisory is not None and advisory.package.lower() in entry.names:
        return True
    return any(_mentions(text, name) for name in entry.names)


def _mentions(text: str, name: str) -> bool:
    return re.search(rf"(?<![\w-]){re.escape(name)}(?![\w-])", text, flags=re.IGNORECASE) is not None
