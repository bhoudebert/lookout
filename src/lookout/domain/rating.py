"""What the user thinks of an item: thumbs up, thumbs down, or nothing (ADR 0017)."""

from enum import IntEnum


class Rating(IntEnum):
    """A rating teaches the profile whatever the item's state, and never removes the item."""

    DOWN = -1
    NONE = 0
    UP = 1
