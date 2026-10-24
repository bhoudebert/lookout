"""Severity of an advisory or alert."""

from enum import IntEnum


class Severity(IntEnum):
    """Ordered from least to most severe."""

    LOW = 1
    MODERATE = 2
    HIGH = 3
    CRITICAL = 4

    @classmethod
    def parse(cls, text: str) -> "Severity | None":
        """Read a severity word as sources spell it; ``None`` when unknown."""
        words = {
            "low": cls.LOW,
            "moderate": cls.MODERATE,
            "medium": cls.MODERATE,
            "high": cls.HIGH,
            "critical": cls.CRITICAL,
        }
        return words.get(text.strip().lower())
