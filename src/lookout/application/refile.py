"""File existing items again after categories change (ADR 0014)."""

from collections.abc import Callable
from dataclasses import dataclass

from lookout.application.ports import ItemRepository
from lookout.domain.channel import OTHER, ChannelCatalogue


@dataclass(frozen=True, slots=True)
class RefileReport:
    """What filing again did."""

    filed: int
    queued: int


class Refile:
    """Moves items to the categories their sources allow now."""

    def __init__(self, items: ItemRepository, catalogue: Callable[[], ChannelCatalogue]) -> None:
        self._items = items
        self._catalogue = catalogue

    def run(self) -> RefileReport:
        """File by rule what a source decides, and queue for the model what still sits in ``Other``.

        An item whose sources allow exactly one category goes there. An item in ``Other`` whose sources allow
        several is read again at the next run, so the model can choose. Nothing else changes.
        """
        catalogue = self._catalogue()
        filed = queued = 0
        for item in self._items.all():
            allowed = catalogue.allowed(item.sources)
            if len(allowed) == 1:
                target = allowed[0].name
                if item.channel != target:
                    self._items.save(item.filed_in(target))
                    filed += 1
            elif item.channel == OTHER and item.enrichment is not None and len(allowed) > 1:
                self._items.save(item.to_read_again())
                queued += 1
        return RefileReport(filed, queued)
