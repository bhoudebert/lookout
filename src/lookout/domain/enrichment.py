"""What the model says about an item."""

from dataclasses import dataclass

MAX_TAGS = 5
MAX_SCORE = 100


@dataclass(frozen=True, slots=True)
class Enrichment:
    """Summary, category, tags and importance score of one item, as validated from the model's answer."""

    summary: str
    category: str
    tags: tuple[str, ...]
    score: int
    action_needed: bool
    reason: str

    def __post_init__(self) -> None:
        if not 0 <= self.score <= MAX_SCORE:
            msg = f"score must be between 0 and {MAX_SCORE}, got {self.score}"
            raise ValueError(msg)
        if len(self.tags) > MAX_TAGS:
            msg = f"at most {MAX_TAGS} tags, got {len(self.tags)}"
            raise ValueError(msg)
