"""The sources as the user sees them: declared ones with their health, switchable (openspec: dashboard)."""

from dataclasses import dataclass, replace
from datetime import datetime

from lookout.application.ports_sources import SourceStatusRepository


class UnknownSourceError(Exception):
    """No declared source has this name."""


class DisabledInConfigError(Exception):
    """The configuration file turns this source off; only the file can turn it on."""


@dataclass(frozen=True, slots=True)
class DeclaredSource:
    """A source from the configuration."""

    name: str
    kind: str
    enabled: bool


@dataclass(frozen=True, slots=True)
class SourceView:
    """A source and how it is doing."""

    name: str
    kind: str
    enabled: bool
    last_run: datetime | None
    last_error: str | None
    items_seen: int


class SourceDirectory:
    """Lists sources and switches them on and off without editing the configuration."""

    def __init__(self, declared: tuple[DeclaredSource, ...], statuses: SourceStatusRepository) -> None:
        self._declared = declared
        self._statuses = statuses

    def list(self) -> tuple[SourceView, ...]:
        """Every declared source with its last run; one switched off in the dashboard shows as disabled."""
        views: list[SourceView] = []
        for source in self._declared:
            status = self._statuses.get(source.name)
            enabled = source.enabled and not status.disabled
            views.append(
                SourceView(
                    source.name, source.kind, enabled, status.last_run, status.last_error, status.items_seen
                )
            )
        return tuple(views)

    def set_enabled(self, name: str, *, enabled: bool) -> SourceView:
        """Switch a declared source on or off."""
        declared = next((s for s in self._declared if s.name == name), None)
        if declared is None:
            raise UnknownSourceError(name)
        if enabled and not declared.enabled:
            raise DisabledInConfigError(name)
        status = self._statuses.get(name)
        self._statuses.save(replace(status, disabled=not enabled))
        return next(view for view in self.list() if view.name == name)
