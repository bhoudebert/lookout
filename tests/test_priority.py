"""Priority levels: scenarios from openspec/specs/priority."""

import pytest

from lookout.domain.priority import Priority


def test_p0_is_the_most_urgent_level() -> None:
    assert min(Priority.P2, Priority.P0, Priority.P3) is Priority.P0


@pytest.mark.parametrize(
    ("level", "label"),
    [
        (Priority.P0, "act today"),
        (Priority.P1, "this week"),
        (Priority.P2, "read when free"),
        (Priority.P3, "background"),
    ],
)
def test_each_level_says_what_to_do(level: Priority, label: str) -> None:
    assert level.label == label
