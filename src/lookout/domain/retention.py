"""How long things stay: entries at the door, rules, and untouched items (ADR 0016)."""

from dataclasses import dataclass, field
from datetime import datetime, timedelta

from lookout.domain.priority import Priority
from lookout.domain.state import State

DEFAULT_EXPIRY: dict[Priority, int | None] = {
    Priority.P0: None,
    Priority.P1: 30,
    Priority.P2: 14,
    Priority.P3: 7,
}


@dataclass(frozen=True, slots=True)
class Retention:
    """``max_age_days`` and ``rules_window_days`` of 0 mean no limit; an expiry of ``None`` means never."""

    max_age_days: int = 30
    rules_window_days: int = 30
    expire_after_days: dict[Priority, int | None] = field(default_factory=lambda: dict(DEFAULT_EXPIRY))

    def expiry(self, priority: Priority) -> timedelta | None:
        """How long an untouched item of this priority stays in the inbox."""
        days = self.expire_after_days.get(priority)
        return None if days is None else timedelta(days=days)

    def has_expired(
        self, state: State, priority: Priority, published_at: datetime, now: datetime, *, starred: bool
    ) -> bool:
        """Whether an item should now move to ``expired``: untouched, not starred, older than its limit."""
        limit = self.expiry(priority)
        return (
            state in (State.NEW, State.SEEN)
            and not starred
            and limit is not None
            and now - published_at > limit
        )
