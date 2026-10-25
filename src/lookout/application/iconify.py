"""Ask the model for an icon for each category that has none (openspec: categories)."""

from dataclasses import dataclass

from lookout.application.ports_sources import EnrichmentError, IconSuggester
from lookout.application.registry import Registry
from lookout.domain.channel import clean_icon


@dataclass(frozen=True, slots=True)
class IconReport:
    """What a pass did."""

    suggested: int = 0
    failed: bool = False


class Iconify:
    """Gives categories an icon. A category the model has no icon for is marked as having none."""

    def __init__(self, registry: Registry, suggester: IconSuggester) -> None:
        self._registry = registry
        self._suggester = suggester

    def run(self, *, again: bool = False) -> IconReport:
        """Suggest an icon for each category never asked about; with ``again`` also for those without one.

        An icon somebody chose is never replaced.

        Stops at the first failure of the model (it is down) and leaves the rest for the next pass.
        """
        suggested = 0
        for channel in self._registry.channels():
            if channel.icon or (channel.icon == "" and not again):
                continue
            try:
                icon = clean_icon(self._suggester.suggest_icon(channel))
            except EnrichmentError:
                return IconReport(suggested, failed=True)
            self._registry.update_channel(channel.name, icon=icon)
            suggested += bool(icon)
        return IconReport(suggested)
