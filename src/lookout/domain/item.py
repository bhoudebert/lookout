"""The item: one piece of content from a source, and its triage lifecycle (ADR 0011)."""

import hashlib
from dataclasses import dataclass, field, replace
from datetime import datetime
from typing import Self

from lookout.domain.advisory import Advisory
from lookout.domain.channel import OTHER
from lookout.domain.enrichment import Enrichment
from lookout.domain.priority import Priority
from lookout.domain.rating import Rating
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
    rating: Rating = Rating.NONE
    rated_at: datetime | None = None
    boost: int = 0
    author: str = ""
    channel: str = OTHER
    feed_tags: tuple[str, ...] = ()
    extra: dict[str, str] = field(default_factory=dict[str, str])

    # Triage ---------------------------------------------------------------------------------------------

    def open(self) -> Self:
        """Opening a new item makes it seen; any other state is unchanged."""
        if self.state is State.NEW:
            return replace(self, state=State.SEEN)
        return self

    def mark_done(self) -> Self:
        """Out of the inbox. It teaches nothing: taste is said with a rating."""
        return replace(self, state=State.DONE, snoozed_until=None)

    def expire(self) -> Self:
        """The system's doing, not the user's: nobody looked at it in time. Reopening undoes it."""
        return replace(self, state=State.EXPIRED, snoozed_until=None)

    def snooze(self, until: datetime) -> Self:
        """Hide the item until ``until``."""
        return replace(self, state=State.SNOOZED, snoozed_until=until)

    def reopen(self) -> Self:
        """Bring a done, snoozed or expired item back as seen."""
        if self.state in (State.NEW, State.SEEN):
            msg = f"item {self.id} is already in the inbox"
            raise InvalidTransitionError(msg)
        return replace(self, state=State.SEEN, snoozed_until=None)

    def wake(self, now: datetime) -> Self:
        """A snoozed item whose time has come returns as new."""
        if self.state is State.SNOOZED and self.snoozed_until is not None and self.snoozed_until <= now:
            return replace(self, state=State.NEW, snoozed_until=None)
        return self

    def restored(
        self,
        state: State,
        snoozed_until: datetime | None,
        *,
        starred: bool,
        rating: Rating = Rating.NONE,
        rated_at: datetime | None = None,
    ) -> Self:
        """Put the triage fields back as they were, for undo."""
        return replace(
            self, state=state, snoozed_until=snoozed_until, starred=starred, rating=rating, rated_at=rated_at
        )

    def rated(self, rating: Rating, at: datetime) -> Self:
        """Set the rating; the one the item already has clears it (the same thumb pressed twice)."""
        return self.with_rating(Rating.NONE if rating is self.rating else rating, at)

    def with_rating(self, rating: Rating, at: datetime) -> Self:
        """Set the rating exactly, as a group is rated: items already rated that way stay so."""
        return replace(self, rating=rating, rated_at=None if rating is Rating.NONE else at)

    def star(self, *, starred: bool = True) -> Self:
        """Set or clear the star, in any state."""
        return replace(self, starred=starred)

    # Assessment -----------------------------------------------------------------------------------------

    def enriched(self, enrichment: Enrichment) -> Self:
        """Attach the model's reading; the item is filed in the channel it chose."""
        return replace(self, enrichment=enrichment, enrichment_failed=False, channel=enrichment.channel)

    def enrichment_gave_up(self) -> Self:
        """The model never produced a valid answer; the item stays, flagged."""
        return replace(self, enrichment_failed=True)

    def ranked(self, boost: int) -> Self:
        """Set the personal rank adjustment; it orders items inside a priority band."""
        return replace(self, boost=boost)

    def filed_in(self, channel: str) -> Self:
        """Put the item in a channel by rule, keeping what the model said about it."""
        reading = replace(self.enrichment, channel=channel) if self.enrichment is not None else None
        return replace(self, channel=channel, enrichment=reading)

    def to_read_again(self) -> Self:
        """Forget the model's reading so the next run reads it again; the priority is recomputed then."""
        return replace(self, enrichment=None, enrichment_failed=False)

    def assessed(self, priority: Priority, reason: str, stack_matches: tuple[str, ...]) -> Self:
        """Record the priority decided by the policy, why, and the stack entries matched."""
        return replace(self, priority=priority, priority_reason=reason, stack_matches=stack_matches)
