"""The item: one piece of content from a source, and its triage lifecycle (ADR 0011)."""

import hashlib
from dataclasses import dataclass, field, replace
from datetime import datetime
from typing import Self

from lookout.domain.advisory import Advisory
from lookout.domain.enrichment import Enrichment
from lookout.domain.priority import Priority
from lookout.domain.state import State
from lookout.domain.urls import canonical_url


class InvalidTransitionError(Exception):
    """A triage action that makes no sense in the item's current state."""


def item_id(url: str) -> str:
    """Stable id of an item: the same canonical URL is the same item whatever the source."""
    return hashlib.sha256(canonical_url(url).encode()).hexdigest()[:16]


@dataclass(frozen=True, slots=True)
class Item:
    """An item and everything Lookout knows about it. Methods return new items; nothing mutates."""

    id: str
    url: str
    title: str
    body: str
    published_at: datetime
    sources: tuple[str, ...]
    advisory: Advisory | None = None
    enrichment: Enrichment | None = None
    enrichment_failed: bool = False
    stack_matches: tuple[str, ...] = ()
    priority: Priority = Priority.P3
    priority_reason: str = "not yet assessed"
    state: State = State.NEW
    snoozed_until: datetime | None = None
    starred: bool = False
    extra: dict[str, str] = field(default_factory=dict[str, str])

    # Triage ---------------------------------------------------------------------------------------------

    def open(self) -> Self:
        """Opening a new item makes it seen; any other state is unchanged."""
        if self.state is State.NEW:
            return replace(self, state=State.SEEN)
        return self

    def mark_done(self) -> Self:
        """The user handled it."""
        return replace(self, state=State.DONE, snoozed_until=None)

    def dismiss(self) -> Self:
        """The user does not want it."""
        return replace(self, state=State.DISMISSED, snoozed_until=None)

    def snooze(self, until: datetime) -> Self:
        """Hide the item until ``until``."""
        return replace(self, state=State.SNOOZED, snoozed_until=until)

    def reopen(self) -> Self:
        """Bring a done, dismissed or snoozed item back as seen."""
        if self.state in (State.NEW, State.SEEN):
            msg = f"item {self.id} is already in the inbox"
            raise InvalidTransitionError(msg)
        return replace(self, state=State.SEEN, snoozed_until=None)

    def wake(self, now: datetime) -> Self:
        """A snoozed item whose time has come returns as new."""
        if self.state is State.SNOOZED and self.snoozed_until is not None and self.snoozed_until <= now:
            return replace(self, state=State.NEW, snoozed_until=None)
        return self

    def star(self, *, starred: bool = True) -> Self:
        """Set or clear the star, in any state."""
        return replace(self, starred=starred)

    # Assessment -----------------------------------------------------------------------------------------

    def enriched(self, enrichment: Enrichment) -> Self:
        """Attach the model's reading."""
        return replace(self, enrichment=enrichment, enrichment_failed=False)

    def enrichment_gave_up(self) -> Self:
        """The model never produced a valid answer; the item stays, flagged."""
        return replace(self, enrichment_failed=True)

    def assessed(self, priority: Priority, reason: str, stack_matches: tuple[str, ...]) -> Self:
        """Record the priority decided by the policy, why, and the stack entries matched."""
        return replace(self, priority=priority, priority_reason=reason, stack_matches=stack_matches)
