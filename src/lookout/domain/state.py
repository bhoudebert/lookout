"""Triage states of an item (ADR 0011)."""

from enum import StrEnum


class State(StrEnum):
    """Where an item stands in the user's inbox. Starring is independent of the state."""

    NEW = "new"
    SEEN = "seen"
    DONE = "done"
    SNOOZED = "snoozed"
    DISMISSED = "dismissed"
