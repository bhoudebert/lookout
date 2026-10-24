"""Item lifecycle rules not reached through the use cases (openspec: triage, enrichment)."""

from datetime import timedelta

from tests.support import NOW, make_item

from lookout.domain.state import State


def test_waking_an_item_that_is_not_snoozed_changes_nothing() -> None:
    item = make_item()
    assert item.wake(NOW) is item


def test_snoozed_item_does_not_wake_early() -> None:
    item = make_item().snooze(NOW + timedelta(hours=1))
    assert item.wake(NOW).state is State.SNOOZED


def test_item_whose_enrichment_failed_stays_visible_and_flagged() -> None:
    item = make_item().enrichment_gave_up()
    assert (item.enrichment_failed, item.state) == (True, State.NEW)
