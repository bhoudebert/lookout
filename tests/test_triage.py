"""Scenarios of openspec/specs/triage."""

from datetime import timedelta

import pytest
from tests.support import NOW, FixedClock, database, make_item, triage_for

from lookout.adapters.store.sqlite import SqliteItemRepository
from lookout.application.ports import InboxQuery
from lookout.application.triage import Action, Inbox, ItemNotFoundError, Triage
from lookout.domain.item import InvalidTransitionError
from lookout.domain.priority import Priority
from lookout.domain.state import State


def setup() -> tuple[Triage, Inbox, FixedClock, object]:
    db = database()
    repo = SqliteItemRepository(db)
    clock = FixedClock()
    return triage_for(repo, db, clock)[0], Inbox(repo, clock), clock, repo


def test_opening_a_new_item_makes_it_seen() -> None:
    triage, _, _, repo = setup()
    item = make_item()
    repo.save(item)  # type: ignore[attr-defined]
    assert triage.act(item.id, Action.OPEN).after.state is State.SEEN


def test_opening_a_done_item_leaves_it_done() -> None:
    triage, _, _, repo = setup()
    item = make_item().mark_done()
    repo.save(item)  # type: ignore[attr-defined]
    assert triage.act(item.id, Action.OPEN).after.state is State.DONE


def test_done_and_dismissed_items_leave_the_inbox() -> None:
    triage, inbox, _, repo = setup()
    keep, done, dismissed = (
        make_item("https://a.test/1"),
        make_item("https://a.test/2"),
        make_item("https://a.test/3"),
    )
    for item in (keep, done, dismissed):
        repo.save(item)  # type: ignore[attr-defined]
    triage.act(done.id, Action.DONE)
    triage.act(dismissed.id, Action.DISMISS)
    assert [i.id for i in inbox.list().items] == [keep.id]


def test_snoozed_item_returns_as_new_when_its_time_passes() -> None:
    triage, inbox, clock, repo = setup()
    item = make_item()
    repo.save(item)  # type: ignore[attr-defined]
    triage.act(item.id, Action.SNOOZE, until=NOW + timedelta(hours=1))
    assert inbox.list().total == 0
    clock.advance(hours=1, minutes=1)
    page = inbox.list()
    assert [(i.id, i.state) for i in page.items] == [(item.id, State.NEW)]


def test_snoozed_item_stays_hidden_before_its_time() -> None:
    triage, inbox, clock, repo = setup()
    item = make_item()
    repo.save(item)  # type: ignore[attr-defined]
    triage.act(item.id, Action.SNOOZE, until=NOW + timedelta(hours=2))
    clock.advance(hours=1)
    assert inbox.wake_due() == 0
    assert inbox.list().total == 0


def test_snoozing_needs_a_wake_up_time() -> None:
    triage, _, _, repo = setup()
    item = make_item()
    repo.save(item)  # type: ignore[attr-defined]
    with pytest.raises(ValueError, match="wake-up time"):
        triage.act(item.id, Action.SNOOZE)


def test_reopen_brings_back_done_dismissed_and_snoozed_items() -> None:
    for how in (Action.DONE, Action.DISMISS):
        triage, _, _, repo = setup()
        item = make_item()
        repo.save(item)  # type: ignore[attr-defined]
        triage.act(item.id, how)
        assert triage.act(item.id, Action.REOPEN).after.state is State.SEEN
    triage, _, _, repo = setup()
    item = make_item()
    repo.save(item)  # type: ignore[attr-defined]
    triage.act(item.id, Action.SNOOZE, until=NOW + timedelta(days=1))
    after = triage.act(item.id, Action.REOPEN).after
    assert (after.state, after.snoozed_until) == (State.SEEN, None)


def test_reopening_an_item_already_in_the_inbox_is_refused() -> None:
    triage, _, _, repo = setup()
    item = make_item()
    repo.save(item)  # type: ignore[attr-defined]
    with pytest.raises(InvalidTransitionError):
        triage.act(item.id, Action.REOPEN)


def test_star_is_independent_of_state() -> None:
    triage, _, _, repo = setup()
    item = make_item()
    repo.save(item)  # type: ignore[attr-defined]
    triage.act(item.id, Action.DONE)
    starred = triage.act(item.id, Action.STAR).after
    assert (starred.starred, starred.state) == (True, State.DONE)
    assert triage.act(item.id, Action.UNSTAR).after.starred is False


def test_unknown_item_is_reported() -> None:
    triage, *_ = setup()
    with pytest.raises(ItemNotFoundError):
        triage.act("nope", Action.DONE)


def test_last_action_can_be_undone() -> None:
    triage, inbox, _, repo = setup()
    item = make_item()
    repo.save(item)  # type: ignore[attr-defined]
    outcome = triage.act(item.id, Action.DISMISS)
    assert inbox.list().total == 0
    triage.undo(outcome)
    assert [i.id for i in inbox.list().items] == [item.id]


def test_bulk_action_applies_to_every_item() -> None:
    triage, inbox, _, repo = setup()
    items = [make_item(f"https://a.test/{n}") for n in range(3)]
    for item in items:
        repo.save(item)  # type: ignore[attr-defined]
    outcomes = triage.act_many(tuple(i.id for i in items), Action.DONE)
    assert len(outcomes) == 3
    assert inbox.list().total == 0


def test_mark_everything_below_a_priority_as_seen() -> None:
    triage, _, _, repo = setup()
    urgent = make_item("https://a.test/u", priority=Priority.P0)
    p1 = make_item("https://a.test/p1", priority=Priority.P1)
    p2 = make_item("https://a.test/p2", priority=Priority.P2)
    p3 = make_item("https://a.test/p3", priority=Priority.P3)
    for item in (urgent, p1, p2, p3):
        repo.save(item)  # type: ignore[attr-defined]
    assert triage.mark_seen_below(Priority.P1) == 2
    states = {i.id: i.state for i in repo.all()}  # type: ignore[attr-defined]
    assert states == {urgent.id: State.NEW, p1.id: State.NEW, p2.id: State.SEEN, p3.id: State.SEEN}


def test_inbox_can_be_queried_with_explicit_filters() -> None:
    _, inbox, _, repo = setup()
    repo.save(make_item("https://a.test/1").mark_done())  # type: ignore[attr-defined]
    assert inbox.list(InboxQuery(states=frozenset({State.DONE}))).total == 1
