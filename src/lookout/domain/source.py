"""A source as the user defines it: a river that flows into the inbox (ADR 0013)."""

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True, slots=True)
class SourceDef:
    """What the user configures for one source. ``settings`` are the fields its ``type`` takes."""

    name: str
    type: str
    settings: dict[str, Any] = field(default_factory=dict[str, Any])
    channels: tuple[str, ...] = ()
    keywords: tuple[str, ...] = ()
    enabled: bool = True
    model: str = ""
    """The model that reads this source's items; empty means the one of ``llm``."""
