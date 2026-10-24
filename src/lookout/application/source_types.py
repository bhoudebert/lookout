"""What each type of source takes, published so a form can be built from it (openspec: source-management)."""

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class FieldInfo:
    """One setting of a source type; ``kind`` is text, list (one per line), bool or number."""

    name: str
    label: str
    kind: str
    required: bool = False
    default: Any = None
    help: str = ""


@dataclass(frozen=True, slots=True)
class SourceTypeInfo:
    """A type of source and its settings, besides the name, channels and keywords every source has."""

    name: str
    label: str
    description: str
    fields: tuple[FieldInfo, ...]
