"""Categories (channels in the code): a hierarchy the user defines, and the catalogue (ADR 0015)."""

import unicodedata
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field

OTHER = "Other"
SEP = " > "
MAX_DEPTH = 4
MAX_SEGMENT_CHARS = 40
MAX_ICON_CHARS = 12
_ICON_JOINERS = frozenset({"\u200d", "\ufe0f"})


class UnknownChannelError(Exception):
    """A source names a category that is not declared."""


class InvalidCategoryError(Exception):
    """A category path that cannot be used."""


def normalize(path: str) -> str:
    """``" Dev>  Rust "`` becomes ``"Dev > Rust"``. Raises when a name is empty, too long or too deep."""
    parts = [part.strip() for part in path.split(">")]
    if not path.strip() or any(not part for part in parts):
        msg = "a category is a name, or names joined by '>', none of them empty"
        raise InvalidCategoryError(msg)
    if len(parts) > MAX_DEPTH:
        msg = f"a category has at most {MAX_DEPTH} levels"
        raise InvalidCategoryError(msg)
    if any(len(part) > MAX_SEGMENT_CHARS for part in parts):
        msg = f"each name of a category has at most {MAX_SEGMENT_CHARS} characters"
        raise InvalidCategoryError(msg)
    return SEP.join(parts)


def ancestors(path: str) -> tuple[str, ...]:
    """The categories above this one, outermost first: ``A > B > C`` gives ``A`` and ``A > B``."""
    parts = path.split(SEP)
    return tuple(SEP.join(parts[:n]) for n in range(1, len(parts)))


def is_within(path: str, ancestor: str) -> bool:
    """Whether ``path`` is ``ancestor`` or somewhere under it, ignoring case."""
    p, a = path.lower(), ancestor.lower()
    return p == a or p.startswith(a + SEP.lower())


def leaf(path: str) -> str:
    """The last name of a path."""
    return path.rsplit(SEP, maxsplit=1)[-1]


def clean_icon(text: str) -> str:
    """The text when it is one emoji, else an empty string: an icon is never text, digits or markup."""
    text = text.strip()
    if not text or len(text) > MAX_ICON_CHARS:
        return ""
    if unicodedata.category(text[0]) not in ("So", "Sk"):
        return ""
    ok = all(unicodedata.category(c) in ("So", "Sk") or c in _ICON_JOINERS for c in text)
    return text if ok else ""


@dataclass(frozen=True, slots=True)
class Channel:
    """A category with a one-line description the model can use. ``name`` is the whole path.

    ``icon`` is one emoji; ``None`` means nobody chose one yet, an empty string that none is wanted.
    """

    name: str
    description: str = ""
    icon: str | None = None


@dataclass(frozen=True, slots=True)
class ChannelCatalogue:
    """The declared categories and which of them each source may feed. ``Other`` always exists."""

    channels: tuple[Channel, ...] = (Channel(OTHER),)
    routes: Mapping[str, tuple[str, ...]] = field(default_factory=dict[str, tuple[str, ...]])

    def __post_init__(self) -> None:
        if not any(c.name.lower() == OTHER.lower() for c in self.channels):
            object.__setattr__(self, "channels", (*self.channels, Channel(OTHER)))
        known = {c.name.lower() for c in self.channels}
        for source, names in self.routes.items():
            for name in names:
                if name.lower() not in known:
                    msg = f"source '{source}' feeds the channel '{name}', which is not declared"
                    raise UnknownChannelError(msg)

    def allowed(self, sources: Iterable[str]) -> tuple[Channel, ...]:
        """What these sources allow: each listed category and what is under it, or all if one lists none."""
        listed: list[str] = []
        for source in sources:
            names = self.routes.get(source, ())
            if not names:
                return self.channels
            listed.extend(names)
        found = tuple(c for c in self.channels if any(is_within(c.name, name) for name in listed))
        return found or self.channels

    def initial(self, sources: Iterable[str]) -> str:
        """Where an item goes before a model has read it: the one category allowed, else ``Other``."""
        allowed = self.allowed(sources)
        return allowed[0].name if len(allowed) == 1 else OTHER

    def children_of(self, path: str) -> tuple[Channel, ...]:
        """Every category under ``path``."""
        return tuple(c for c in self.channels if c.name.lower() != path.lower() and is_within(c.name, path))
