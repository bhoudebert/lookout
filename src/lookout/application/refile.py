"""File existing items again after categories change (ADR 0014, 0015)."""

from collections.abc import Callable
from dataclasses import dataclass

from lookout.application.ports import ItemRepository
from lookout.domain.channel import OTHER, ChannelCatalogue


@dataclass(frozen=True, slots=True)
class RefileReport:
    """What filing again did, or would do."""

    filed: int
    queued: int


class Refile:
    """Moves items to the most specific categories their sources allow now."""

    def __init__(self, items: ItemRepository, catalogue: Callable[[], ChannelCatalogue]) -> None:
        self._items = items
        self._catalogue = catalogue

    def run(self, *, dry_run: bool = False) -> RefileReport:
        """File by rule what a source decides, and queue for the model what could now go deeper.

        An item the model read that sits in ``Other`` or in a category with subcategories now is read again at
        the next run, so the model can go deeper. An item whose sources allow exactly one category goes there,
        and so does an unread one in ``Other`` whose sources name one (the model then goes deeper).
        With ``dry_run`` nothing changes and the report says what would.
        """
        catalogue = self._catalogue()
        filed = queued = 0
        for item in self._items.all():
            allowed = catalogue.allowed(item.sources)
            if len(allowed) == 1:
                target = allowed[0].name
                if item.channel != target:
                    if not dry_run:
                        self._items.save(item.filed_in(target))
                    filed += 1
            elif (
                item.enrichment is None
                and item.channel == OTHER
                and (target := catalogue.initial(item.sources)) != OTHER
            ):
                # Not read yet, and its sources name one category: it waits there, not in Other.
                if not dry_run:
                    self._items.save(item.filed_in(target))
                filed += 1
            elif item.enrichment is not None and (
                item.channel == OTHER or catalogue.children_of(item.channel)
            ):
                if not dry_run:
                    self._items.save(item.to_read_again())
                queued += 1
        return RefileReport(filed, queued)
