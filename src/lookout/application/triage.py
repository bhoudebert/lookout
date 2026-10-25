"""Triage use cases: act on items and read the inbox (openspec: triage)."""

from collections.abc import Callable
from dataclasses import dataclass, replace
from datetime import datetime
from enum import StrEnum

from lookout.application.ports import Clock, Feedback, InboxQuery, ItemRepository, Page
from lookout.domain.item import Item
from lookout.domain.priority import Priority
from lookout.domain.profile import SignalKind
from lookout.domain.rating import Rating
from lookout.domain.state import State

MAX_SWEEP = 5000
"""The most items one sweep may touch; a bigger filter must be narrowed first."""


class ItemNotFoundError(Exception):
    """No item has this id."""


class TooManyItemsError(Exception):
    """A filter matches more items than one sweep may touch."""

    def __init__(self, matched: int) -> None:
        super().__init__(f"{matched} items match; narrow the filter to at most {MAX_SWEEP}")
        self.matched = matched


class Action(StrEnum):
    """What the user can do to an item."""

    OPEN = "open"
    DONE = "done"
    SNOOZE = "snooze"
    REOPEN = "reopen"
    STAR = "star"
    UNSTAR = "unstar"


@dataclass(frozen=True, slots=True)
class Outcome:
    """The item after an action and before it, so the caller can offer undo."""

    before: Item
    after: Item


@dataclass(frozen=True, slots=True)
class Undo:
    """What an item was like before an action, as a client sends it back."""

    item_id: str
    state: State
    snoozed_until: datetime | None
    starred: bool
    rating: Rating = Rating.NONE
    rated_at: datetime | None = None


@dataclass(frozen=True, slots=True)
class Sweep:
    """What an action on a whole filter matched, a few examples, and (unless it was a dry run) what it did."""

    matched: int
    sample: tuple[Item, ...]
    outcomes: tuple[Outcome, ...] = ()


class Triage:
    """Applies the user's actions to items."""

    def __init__(self, items: ItemRepository, feedback: Feedback, clock: Clock) -> None:
        self._items = items
        self._feedback = feedback
        self._clock = clock

    def act(self, item_id: str, action: Action, *, until: datetime | None = None) -> Outcome:
        """Apply ``action``; ``until`` is required for snoozing."""
        return self.act_many((item_id,), action, until=until)[0]

    def act_many(
        self,
        item_ids: tuple[str, ...],
        action: Action,
        *,
        until: datetime | None = None,
        learn: bool = True,
    ) -> tuple[Outcome, ...]:
        """Apply one action to several items, all or none: a bad id or transition changes nothing.

        With ``learn`` false nothing is recorded for the profile: sweeping a backlog says nothing about taste.
        """
        befores = [self._existing(item_id) for item_id in item_ids]
        outcomes = tuple(Outcome(before, _apply(before, action, until)) for before in befores)
        kind = _SIGNALS.get(action)
        for outcome in outcomes:
            self._items.save(outcome.after)
            if (
                learn
                and kind is not None
                and (action is not Action.OPEN or outcome.before.state is State.NEW)
            ):
                self._feedback.record(outcome.after, kind)
        return outcomes

    def sweep(
        self,
        query: InboxQuery,
        action: Action,
        *,
        until: datetime | None = None,
        dry_run: bool = False,
        sample: int = 5,
    ) -> Sweep:
        """Apply ``action`` to all ``query`` matches, learning nothing; a dry run only counts and samples."""
        page = self._items.search(replace(query, limit=MAX_SWEEP + 1, offset=0))
        if page.total > MAX_SWEEP:
            raise TooManyItemsError(page.total)
        if dry_run:
            return Sweep(page.total, page.items[:sample])
        outcomes = self.act_many(tuple(i.id for i in page.items), action, until=until, learn=False)
        return Sweep(page.total, page.items[:sample], outcomes)

    def _existing(self, item_id: str) -> Item:
        item = self._items.get(item_id)
        if item is None:
            raise ItemNotFoundError(item_id)
        return item

    def mark_seen_below(self, urgent: Priority) -> int:
        """Mark every new item less urgent than ``urgent`` as seen; returns how many changed."""
        less_urgent = frozenset(p for p in Priority if p > urgent)
        page = self._items.search(
            InboxQuery(priorities=less_urgent, states=frozenset({State.NEW}), limit=10_000)
        )
        for item in page.items:
            self._items.save(item.open())
        return len(page.items)

    def rate(self, item_id: str, rating: Rating) -> Outcome:
        """Set the rating (the same one again clears it). The item stays where it is; the profile follows."""
        before = self._existing(item_id)
        after = before.rated(rating, self._clock.now())
        self._items.save(after)
        self._feedback.rated()
        return Outcome(before, after)

    def restore(self, undo: "Undo") -> Item:
        """Put an item's triage fields back as a client remembered them (undo across requests)."""
        return self.restore_many((undo,))[0]

    def restore_many(self, undos: tuple["Undo", ...]) -> tuple[Item, ...]:
        """Put several items back, and refresh the ranks once, since ratings may be among what comes back."""
        restored = tuple(
            self._existing(u.item_id).restored(
                u.state, u.snoozed_until, starred=u.starred, rating=u.rating, rated_at=u.rated_at
            )
            for u in undos
        )
        for item in restored:
            self._items.save(item)
        self._feedback.rated()
        return restored

    def undo(self, outcome: Outcome) -> Item:
        """Put an item back as it was before an action."""
        self._items.save(outcome.before)
        self._feedback.rated()
        return outcome.before


_SIGNALS: dict[Action, SignalKind] = {
    Action.OPEN: SignalKind.OPEN,
    Action.SNOOZE: SignalKind.SNOOZE,
    Action.STAR: SignalKind.STAR,
}

_SIMPLE: dict[Action, Callable[[Item], Item]] = {
    Action.OPEN: Item.open,
    Action.DONE: Item.mark_done,
    Action.REOPEN: Item.reopen,
    Action.STAR: lambda item: item.star(),
    Action.UNSTAR: lambda item: item.star(starred=False),
}


def _apply(item: Item, action: Action, until: datetime | None) -> Item:
    if action is not Action.SNOOZE:
        return _SIMPLE[action](item)
    if until is None:
        msg = "snoozing needs a wake-up time"
        raise ValueError(msg)
    return item.snooze(until)


class Inbox:
    """Reads the inbox, waking snoozed items whose time has come."""

    def __init__(self, items: ItemRepository, clock: Clock) -> None:
        self._items = items
        self._clock = clock

    def list(self, query: InboxQuery | None = None) -> Page:
        """Items matching ``query``; by default what is still to look at."""
        self.wake_due()
        return self._items.search(query or InboxQuery(states=frozenset({State.NEW, State.SEEN})))

    def wake_due(self) -> int:
        """Return snoozed items to new when their time has passed; returns how many woke."""
        now = self._clock.now()
        due = self._items.snoozed_before(now)
        for item in due:
            self._items.save(item.wake(now))
        return len(due)
