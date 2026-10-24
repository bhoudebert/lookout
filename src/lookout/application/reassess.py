"""Recompute priorities of stored items without calling the model (openspec: priority, "Recompute")."""

from lookout.application.ports import ItemRepository
from lookout.domain.policy import PriorityPolicy
from lookout.domain.stack import Stack


class Reassess:
    """Applies the current stack and policy to every stored item."""

    def __init__(self, items: ItemRepository, policy: PriorityPolicy, stack: Stack) -> None:
        self._items = items
        self._policy = policy
        self._stack = stack

    def run(self) -> int:
        """Return the number of items whose priority or matches changed."""
        changed = 0
        for item in self._items.all():
            matches = self._stack.match(f"{item.title}\n{item.body}", item.advisory)
            decision = self._policy.decide(
                advisory=item.advisory, stack_matches=matches, enrichment=item.enrichment
            )
            updated = item.assessed(decision.priority, decision.reason, matches)
            if updated != item:
                self._items.save(updated)
                changed += 1
        return changed
