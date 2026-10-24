"""The system clock."""

from datetime import UTC, datetime


class SystemClock:
    """Current time in UTC."""

    def now(self) -> datetime:
        return datetime.now(UTC)
