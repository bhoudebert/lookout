"""Structured facts of a security advisory or alert, used by the priority rules."""

from dataclasses import dataclass

from lookout.domain.severity import Severity


@dataclass(frozen=True, slots=True)
class Advisory:
    """An advisory affecting one package. Fields come from the source, never from the model."""

    severity: Severity
    package: str
    ecosystem: str
    known_exploited: bool = False
    identifiers: tuple[str, ...] = ()
