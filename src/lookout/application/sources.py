"""Sources as the user sees them: their definition and how they are doing (openspec: source-management)."""

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from lookout.application.ports_sources import SourceStatusRepository
from lookout.application.registry import Registry
from lookout.domain.source import SourceDef


@dataclass(frozen=True, slots=True)
class SourceView:
    """A source, its settings and its last run."""

    name: str
    type: str
    enabled: bool
    channels: tuple[str, ...]
    keywords: tuple[str, ...]
    settings: dict[str, Any]
    last_run: datetime | None
    last_error: str | None
    items_seen: int


class SourceDirectory:
    """Joins the definitions with the health of each source."""

    def __init__(self, registry: Registry, statuses: SourceStatusRepository) -> None:
        self._registry = registry
        self._statuses = statuses

    def list(self) -> tuple[SourceView, ...]:
        """Every source with its last run."""
        return tuple(self.view(source) for source in self._registry.sources())

    def view(self, source: SourceDef) -> SourceView:
        """One source with its last run."""
        status = self._statuses.get(source.name)
        return SourceView(
            name=source.name,
            type=source.type,
            enabled=source.enabled,
            channels=source.channels,
            keywords=source.keywords,
            settings=source.settings,
            last_run=status.last_run,
            last_error=status.last_error,
            items_seen=status.items_seen,
        )
