"""Adding, changing and deleting sources and channels (openspec: source-management, ADR 0013)."""

from collections.abc import Callable
from dataclasses import replace
from typing import Protocol

from lookout.domain.channel import OTHER, Channel, ChannelCatalogue
from lookout.domain.source import SourceDef


class RegistryError(Exception):
    """A change to sources or channels that cannot be made."""


class NotFoundError(RegistryError):
    """No source or channel has this name."""


class DuplicateError(RegistryError):
    """The name is taken, ignoring case."""


class InvalidError(RegistryError):
    """The values are not acceptable; the message says which and why."""


class InUseError(RegistryError):
    """A channel that sources still feed, or the channel that must always exist."""


class SourceDefinitions(Protocol):
    """Where source definitions are kept."""

    def all(self) -> tuple[SourceDef, ...]: ...

    def save(self, source: SourceDef) -> None: ...

    def delete(self, name: str) -> None: ...


class ChannelDefinitions(Protocol):
    """Where channel definitions are kept."""

    def all(self) -> tuple[Channel, ...]: ...

    def save(self, channel: Channel) -> None: ...

    def delete(self, name: str) -> None: ...


class Flags(Protocol):
    """Things that happened once."""

    def is_set(self, name: str) -> bool: ...

    def set(self, name: str) -> None: ...


SEEDED = "seeded"


class Registry:
    """The user's sources and channels. ``validate`` raises ``InvalidError`` for unusable settings."""

    def __init__(
        self,
        sources: SourceDefinitions,
        channels: ChannelDefinitions,
        flags: Flags,
        validate: Callable[[SourceDef], None],
    ) -> None:
        self._flags = flags
        self._sources = sources
        self._channels = channels
        self._validate = validate

    # Seeding

    def seed(self, sources: tuple[SourceDef, ...], channels: tuple[Channel, ...]) -> None:
        """On the very first start, store the file's channels and sources. Later starts change nothing.

        The marker is explicit, so deleting every source never brings them back. ``Other`` always exists.
        """
        if not self._flags.is_set(SEEDED):
            # Building the catalogue refuses a source that feeds a channel nobody declared.
            ChannelCatalogue(channels, {s.name: s.channels for s in sources})
            for channel in channels:
                self._channels.save(channel)
            for source in sources:
                self._validate(source)
                self._sources.save(source)
            self._flags.set(SEEDED)
        if not any(c.name.lower() == OTHER.lower() for c in self._channels.all()):
            self._channels.save(Channel(OTHER))

    # Sources

    def sources(self) -> tuple[SourceDef, ...]:
        """Every source, in the order they were added."""
        return self._sources.all()

    def enabled_sources(self) -> tuple[SourceDef, ...]:
        """The sources a run fetches."""
        return tuple(s for s in self._sources.all() if s.enabled)

    def add_source(self, source: SourceDef) -> SourceDef:
        """Store a new source after checking its name, channels and settings."""
        name = source.name.strip()
        if not name:
            msg = "a source needs a name"
            raise InvalidError(msg)
        if self._find(name) is not None:
            msg = f"a source named '{name}' already exists"
            raise DuplicateError(msg)
        stored = self._checked(replace(source, name=name))
        self._sources.save(stored)
        return stored

    def update_source(self, source: SourceDef) -> SourceDef:
        """Replace every setting of an existing source; its name cannot change."""
        existing = self._find(source.name)
        if existing is None:
            raise NotFoundError(source.name)
        stored = self._checked(replace(source, name=existing.name))
        self._sources.save(stored)
        return stored

    def set_enabled(self, name: str, *, enabled: bool) -> SourceDef:
        """Switch a source on or off."""
        existing = self._find(name)
        if existing is None:
            raise NotFoundError(name)
        stored = replace(existing, enabled=enabled)
        self._sources.save(stored)
        return stored

    def remove_source(self, name: str) -> None:
        """Delete a source; its items stay."""
        existing = self._find(name)
        if existing is None:
            raise NotFoundError(name)
        self._sources.delete(existing.name)

    def _find(self, name: str) -> SourceDef | None:
        return next((s for s in self._sources.all() if s.name.lower() == name.strip().lower()), None)

    def _checked(self, source: SourceDef) -> SourceDef:
        by_name = {c.name.lower(): c.name for c in self._channels.all()}
        channels: list[str] = []
        for channel in source.channels:
            canonical = by_name.get(channel.strip().lower())
            if canonical is None:
                msg = f"source '{source.name}' feeds the channel '{channel}', which does not exist"
                raise InvalidError(msg)
            if canonical not in channels:
                channels.append(canonical)
        checked = replace(
            source, channels=tuple(channels), keywords=tuple(k.strip() for k in source.keywords if k.strip())
        )
        self._validate(checked)
        return checked

    # Channels

    def channels(self) -> tuple[Channel, ...]:
        """Every channel, in the order they were added."""
        return self._channels.all()

    def add_channel(self, channel: Channel) -> Channel:
        """Store a new channel."""
        name = channel.name.strip()
        if not name:
            msg = "a channel needs a name"
            raise InvalidError(msg)
        if self._channel(name) is not None:
            msg = f"a channel named '{name}' already exists"
            raise DuplicateError(msg)
        stored = Channel(name, channel.description.strip())
        self._channels.save(stored)
        return stored

    def update_channel(self, name: str, description: str) -> Channel:
        """Change a channel's description."""
        existing = self._channel(name)
        if existing is None:
            raise NotFoundError(name)
        stored = Channel(existing.name, description.strip())
        self._channels.save(stored)
        return stored

    def remove_channel(self, name: str) -> None:
        """Delete a channel no source feeds; ``Other`` stays."""
        existing = self._channel(name)
        if existing is None:
            raise NotFoundError(name)
        if existing.name.lower() == OTHER.lower():
            msg = f"the channel {OTHER} always exists"
            raise InUseError(msg)
        feeders = [
            s.name for s in self._sources.all() if existing.name.lower() in (c.lower() for c in s.channels)
        ]
        if feeders:
            msg = f"the channel '{existing.name}' is fed by {', '.join(feeders)}: change those sources first"
            raise InUseError(msg)
        self._channels.delete(existing.name)

    def _channel(self, name: str) -> Channel | None:
        return next((c for c in self._channels.all() if c.name.lower() == name.strip().lower()), None)

    def catalogue(self) -> ChannelCatalogue:
        """The channels and which of them each source feeds, as the pipeline needs them."""
        return ChannelCatalogue(self._channels.all(), {s.name: s.channels for s in self._sources.all()})
