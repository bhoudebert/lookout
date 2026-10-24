"""Scenario of openspec/specs/priority: "Recompute" after the stack changes, without the model."""

from tests.support import FixedClock, make_item, repository

from lookout.application.reassess import Reassess
from lookout.domain.advisory import Advisory
from lookout.domain.policy import PriorityPolicy
from lookout.domain.priority import Priority
from lookout.domain.severity import Severity
from lookout.domain.stack import Stack, StackEntry


def test_adding_a_package_to_the_stack_raises_existing_advisories() -> None:
    repo = repository()
    item = make_item(advisory=Advisory(Severity.CRITICAL, "django", "pypi"), score=10)
    repo.save(item)

    assert Reassess(repo, PriorityPolicy(), Stack(), FixedClock()).run() == 1
    stored = repo.get(item.id)
    assert stored is not None
    assert stored.priority is Priority.P3

    changed = Reassess(repo, PriorityPolicy(), Stack((StackEntry("django", "pypi"),)), FixedClock())
    assert changed.run() == 1
    stored = repo.get(item.id)
    assert stored is not None
    assert (stored.priority, stored.stack_matches) == (Priority.P0, ("django",))


def test_nothing_changes_when_nothing_differs() -> None:
    repo = repository()
    repo.save(make_item(score=50))
    reassess = Reassess(repo, PriorityPolicy(), Stack(), FixedClock())
    reassess.run()
    assert reassess.run() == 0
