"""Priority levels of an item."""

from enum import IntEnum


class Priority(IntEnum):
    """P0 is the most urgent. A lower number is more urgent, so ``min`` picks the more urgent of two."""

    P0 = 0
    P1 = 1
    P2 = 2
    P3 = 3

    @property
    def label(self) -> str:
        """What the user is asked to do at this level."""
        return _LABELS[self]


_LABELS = {
    Priority.P0: "act today",
    Priority.P1: "this week",
    Priority.P2: "read when free",
    Priority.P3: "background",
}
