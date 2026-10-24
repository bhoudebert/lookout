"""What a source hands over before Lookout makes an item of it."""

from dataclasses import dataclass
from datetime import datetime

from lookout.domain.advisory import Advisory


@dataclass(frozen=True, slots=True)
class RawItem:
    """One entry as a source gave it: markup and all."""

    source: str
    url: str
    title: str
    body: str
    published_at: datetime | None = None
    advisory: Advisory | None = None
    author: str = ""
    tags: tuple[str, ...] = ()
