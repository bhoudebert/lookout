"""Triage states of an item (ADR 0011)."""

from enum import StrEnum


class State(StrEnum):
    """Where an item stands in the user's inbox. Starring is independent of the state.

    ``EXPIRED`` is reached by the system only, when nobody looked at the item for too long (ADR 0016).
    """

    NEW = "new"
    SEEN = "seen"
    DONE = "done"
    SNOOZED = "snoozed"
    DISMISSED = "dismissed"
    EXPIRED = "expired"
