"""Adding, changing and deleting sources and channels (openspec: source-management, ADR 0013)."""

from collections.abc import Callable
from dataclasses import replace
from typing import Protocol

from lookout.application.ports import ItemRepository
from lookout.domain.channel import (
    OTHER,
    SEP,
    Channel,
    ChannelCatalogue,
    InvalidCategoryError,
    ancestors,
    clean_icon,
    is_within,
    normalize,
)
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

    def rename(self, old: str, new: str) -> None: ...

    def delete(self, name: str) -> None: ...


class Flags(Protocol):
    """Things that happened once."""

    def is_set(self, name: str) -> bool: ...

    def set(self, name: str) -> None: ...


SEEDED = "seeded"


def _icon(icon: str | None) -> str | None:
    """The icon as the user gave it: one emoji, empty to have none, ``None`` to let the model suggest one."""
    if icon is None:
        return None
    if not icon.strip():
        return ""
    cleaned = clean_icon(icon)
    if not cleaned:
        msg = "an icon is one emoji"
        raise InvalidError(msg)
    return cleaned


class Registry:
    """The user's sources and channels. ``validate`` raises ``InvalidError`` for unusable settings."""

    def __init__(
        self,
        sources: SourceDefinitions,
        channels: ChannelDefinitions,
        flags: Flags,
        validate: Callable[[SourceDef], None],
        items: ItemRepository,
    ) -> None:
        self._items = items
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
        self._create_missing_parents()

    def _create_missing_parents(self) -> None:
        """Every category has its parents stored, even in a database that kept a path without them."""
        for channel in self._channels.all():
            for parent in ancestors(channel.name):
                if self._channel(parent) is None:
                    self._channels.save(Channel(parent))

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
            canonical = by_name.get(" > ".join(part.strip() for part in channel.split(">")).lower())
            if canonical is None:
                msg = f"source '{source.name}' feeds the channel '{channel}', which does not exist"
                raise InvalidError(msg)
            if canonical not in channels:
                channels.append(canonical)
        checked = replace(
            source,
            channels=tuple(channels),
            keywords=tuple(k.strip() for k in source.keywords if k.strip()),
            model=source.model.strip(),
        )
        self._validate(checked)
        return checked

    # Categories (channels in the code)

    def channels(self) -> tuple[Channel, ...]:
        """Every category, in the order they were added."""
        return self._channels.all()

    def add_channel(self, channel: Channel) -> Channel:
        """Store a new category. A path like ``Dev > Rust`` also creates ``Dev`` when it is missing."""
        try:
            path = normalize(channel.name)
        except InvalidCategoryError as error:
            raise InvalidError(str(error)) from error
        if self._channel(path) is not None:
            msg = f"a category named '{path}' already exists"
            raise DuplicateError(msg)
        for parent in ancestors(path):
            if self._channel(parent) is None:
                self._channels.save(Channel(parent))
        stored = Channel(path, channel.description.strip(), _icon(channel.icon))
        self._channels.save(stored)
        return stored

    def update_channel(self, name: str, description: str | None = None, icon: str | None = None) -> Channel:
        """Change a category's description, icon or both; what is not given stays. An empty icon clears it."""
        existing = self._channel(name)
        if existing is None:
            raise NotFoundError(name)
        stored = Channel(
            existing.name,
            existing.description if description is None else description.strip(),
            existing.icon if icon is None else _icon(icon),
        )
        self._channels.save(stored)
        return stored

    def remove_channel(self, name: str) -> None:
        """Delete a category that has no subcategory and that no source feeds; ``Other`` stays."""
        existing = self._channel(name)
        if existing is None:
            raise NotFoundError(name)
        if existing.name.lower() == OTHER.lower():
            msg = f"the category {OTHER} always exists"
            raise InUseError(msg)
        below = [
            c.name
            for c in self._channels.all()
            if c.name != existing.name and is_within(c.name, existing.name)
        ]
        if below:
            msg = f"the category '{existing.name}' has subcategories ({', '.join(below)}): delete those first"
            raise InUseError(msg)
        feeders = [
            s.name for s in self._sources.all() if any(c.lower() == existing.name.lower() for c in s.channels)
        ]
        if feeders:
            msg = f"the category '{existing.name}' is fed by {', '.join(feeders)}: change those sources first"
            raise InUseError(msg)
        self._channels.delete(existing.name)

    def move_channel(self, name: str, parent: str) -> Channel:
        """Move a category, with everything under it, inside ``parent`` (empty: to the top level).

        Items filed in it and the sources that name it follow. Nothing is lost: a clash with an existing
        category, a move into itself and a path that gets too deep are refused.
        """
        existing = self._channel(name)
        if existing is None:
            raise NotFoundError(name)
        if existing.name.lower() == OTHER.lower():
            msg = f"the category {OTHER} stays where it is"
            raise InUseError(msg)
        target = existing.name.rsplit(SEP, 1)[-1]
        if parent.strip():
            home = self._channel(parent)
            if home is None:
                raise NotFoundError(parent)
            if is_within(home.name, existing.name):
                msg = f"'{existing.name}' cannot move inside itself"
                raise InvalidError(msg)
            target = f"{home.name}{SEP}{target}"
        moved = [c for c in self._channels.all() if is_within(c.name, existing.name)]
        renames = {c.name: target + c.name[len(existing.name) :] for c in moved}
        try:
            for new in renames.values():
                normalize(new)
        except InvalidCategoryError as error:
            raise InvalidError(str(error)) from error
        taken = {c.name.lower() for c in self._channels.all() if c.name not in renames}
        clash = [new for new in renames.values() if new.lower() in taken]
        if clash:
            msg = f"a category named '{clash[0]}' already exists"
            raise DuplicateError(msg)
        if renames[existing.name] == existing.name:
            return existing
        for old, new in renames.items():
            self._channels.rename(old, new)
        self._follow(renames)
        return Channel(renames[existing.name], existing.description, existing.icon)

    def _follow(self, renames: dict[str, str]) -> None:
        """Point the sources and the items that named a moved category at its new path."""
        lowered = {old.lower(): new for old, new in renames.items()}
        for source in self._sources.all():
            if any(c.lower() in lowered for c in source.channels):
                self._sources.save(
                    replace(source, channels=tuple(lowered.get(c.lower(), c) for c in source.channels))
                )
        for item in self._items.all():
            if item.channel.lower() in lowered:
                self._items.save(item.filed_in(lowered[item.channel.lower()]))

    def _channel(self, name: str) -> Channel | None:
        wanted = " > ".join(part.strip() for part in name.split(">")).lower()
        return next((c for c in self._channels.all() if c.name.lower() == wanted), None)

    def models(self) -> dict[str, str]:
        """The model each source asks for, for the sources that ask for one."""
        return {s.name: s.model for s in self._sources.all() if s.model}

    def catalogue(self) -> ChannelCatalogue:
        """The categories and which of them each source feeds, as the pipeline needs them."""
        return ChannelCatalogue(self._channels.all(), {s.name: s.channels for s in self._sources.all()})
