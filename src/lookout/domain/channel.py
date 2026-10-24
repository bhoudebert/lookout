"""Channels: the topics the user looks at, and the catalogue that files items into them (ADR 0012)."""

from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field

OTHER = "Other"


@dataclass(frozen=True, slots=True)
class Channel:
    """A topic with a one-line description the model can use."""

    name: str
    description: str = ""


class UnknownChannelError(Exception):
    """A source names a channel that is not declared."""


@dataclass(frozen=True, slots=True)
class ChannelCatalogue:
    """The declared channels and which of them each source may feed. ``Other`` always exists."""

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

    def _named(self, names: Iterable[str]) -> tuple[Channel, ...]:
        wanted = {n.lower() for n in names}
        return tuple(c for c in self.channels if c.name.lower() in wanted)

    def allowed(self, sources: Iterable[str]) -> tuple[Channel, ...]:
        """The channels these sources allow: what they list, or all of them if one lists none."""
        listed: list[str] = []
        for source in sources:
            names = self.routes.get(source, ())
            if not names:
                return self.channels
            listed.extend(names)
        return self._named(listed) or self.channels

    def initial(self, sources: Iterable[str]) -> str:
        """Where an item goes before a model has read it: the one channel allowed, else ``Other``."""
        allowed = self.allowed(sources)
        return allowed[0].name if len(allowed) == 1 else OTHER
