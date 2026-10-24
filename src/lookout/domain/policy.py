"""Priority policy: rule floors first, the model's score above them (ADR 0002)."""

from dataclasses import dataclass

from lookout.domain.advisory import Advisory
from lookout.domain.enrichment import Enrichment
from lookout.domain.priority import Priority
from lookout.domain.severity import Severity


@dataclass(frozen=True, slots=True)
class Thresholds:
    """Lowest score for each band. Scores below ``p2`` are P3."""

    p0: int = 90
    p1: int = 70
    p2: int = 40


@dataclass(frozen=True, slots=True)
class Decision:
    """A priority and how it was reached."""

    priority: Priority
    reason: str


@dataclass(frozen=True, slots=True)
class PriorityPolicy:
    """Decides the priority of an item from facts first, then from the model."""

    thresholds: Thresholds = Thresholds()

    def decide(
        self,
        *,
        advisory: Advisory | None,
        stack_matches: tuple[str, ...],
        enrichment: Enrichment | None,
        profile_boost: int = 0,
    ) -> Decision:
        """Priority is the more urgent of the rule floor and the banded score."""
        floor = _floor(advisory, stack_matches)
        scored = self._banded(enrichment, profile_boost)
        if floor is not None and (scored is None or floor[0] <= scored[0]):
            return Decision(floor[0], floor[1])
        if scored is not None:
            return Decision(scored[0], scored[1])
        return Decision(Priority.P3, "no rule matched and the model has not scored it yet")

    def _banded(self, enrichment: Enrichment | None, boost: int) -> tuple[Priority, str] | None:
        if enrichment is None:
            return None
        score = max(0, min(100, enrichment.score + boost))
        t = self.thresholds
        if score >= t.p0:
            level = Priority.P0
        elif score >= t.p1:
            level = Priority.P1
        elif score >= t.p2:
            level = Priority.P2
        else:
            level = Priority.P3
        detail = f"score {enrichment.score}" + (f" {boost:+d} from your profile" if boost else "")
        return level, f"model {detail}: {enrichment.reason}"


def _floor(advisory: Advisory | None, stack_matches: tuple[str, ...]) -> tuple[Priority, str] | None:
    """The minimum priority imposed by facts; ``None`` when no rule applies."""
    if advisory is None or not (stack_matches or advisory.watched):
        return None
    ids = ", ".join(advisory.identifiers) or advisory.package
    use = (
        f"{advisory.package}, which you use"
        if stack_matches
        else f"{advisory.package} in a repository you watch"
    )
    if advisory.known_exploited:
        return (
            Priority.P0,
            f"rule: {ids} is known to be exploited and affects {use}",
        )
    if advisory.severity is Severity.CRITICAL:
        return Priority.P0, f"rule: critical advisory {ids} affects {use}"
    if advisory.severity is Severity.HIGH:
        return Priority.P1, f"rule: high severity advisory {ids} affects {use}"
    return None
