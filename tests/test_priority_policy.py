"""Scenarios of openspec/specs/priority."""

import pytest
from tests.support import enrichment

from lookout.domain.advisory import Advisory
from lookout.domain.enrichment import Enrichment
from lookout.domain.policy import PriorityPolicy, Thresholds
from lookout.domain.priority import Priority
from lookout.domain.severity import Severity

policy = PriorityPolicy()
DJANGO = ("django",)


def advisory(severity: Severity, *, kev: bool = False) -> Advisory:
    return Advisory(severity, "django", "pypi", known_exploited=kev, identifiers=("CVE-2026-0001",))


def test_critical_advisory_on_declared_package_is_p0_whatever_the_model_said() -> None:
    decision = policy.decide(
        advisory=advisory(Severity.CRITICAL), stack_matches=DJANGO, enrichment=enrichment(5)
    )
    assert decision.priority is Priority.P0
    assert "critical advisory CVE-2026-0001" in decision.reason


def test_model_cannot_lower_a_floor() -> None:
    decision = policy.decide(advisory=advisory(Severity.HIGH), stack_matches=DJANGO, enrichment=enrichment(5))
    assert decision.priority is Priority.P1


def test_model_can_raise_above_a_floor() -> None:
    decision = policy.decide(
        advisory=advisory(Severity.HIGH), stack_matches=DJANGO, enrichment=enrichment(95)
    )
    assert decision.priority is Priority.P0
    assert decision.reason.startswith("model score 95")


def test_known_exploited_vulnerability_on_declared_package_is_p0() -> None:
    decision = policy.decide(
        advisory=advisory(Severity.MODERATE, kev=True), stack_matches=DJANGO, enrichment=None
    )
    assert decision.priority is Priority.P0
    assert "known to be exploited" in decision.reason


def test_advisory_on_a_package_you_do_not_use_gets_no_floor() -> None:
    decision = policy.decide(
        advisory=advisory(Severity.CRITICAL), stack_matches=(), enrichment=enrichment(10)
    )
    assert decision.priority is Priority.P3


def test_moderate_advisory_has_no_floor() -> None:
    decision = policy.decide(
        advisory=advisory(Severity.MODERATE), stack_matches=DJANGO, enrichment=enrichment(45)
    )
    assert decision.priority is Priority.P2


def test_without_any_signal_an_item_is_background() -> None:
    decision = policy.decide(advisory=None, stack_matches=(), enrichment=None)
    assert decision.priority is Priority.P3
    assert "not scored" in decision.reason


@pytest.mark.parametrize(
    ("score", "expected"),
    [
        (100, Priority.P0),
        (90, Priority.P0),
        (89, Priority.P1),
        (70, Priority.P1),
        (69, Priority.P2),
        (40, Priority.P2),
        (39, Priority.P3),
        (0, Priority.P3),
    ],
)
def test_score_bands(score: int, expected: Priority) -> None:
    assert policy.decide(advisory=None, stack_matches=(), enrichment=enrichment(score)).priority is expected


def test_profile_boost_moves_the_score_and_is_explained() -> None:
    decision = policy.decide(advisory=None, stack_matches=(), enrichment=enrichment(65), profile_boost=10)
    assert decision.priority is Priority.P1
    assert "+10 from your profile" in decision.reason


def test_boosted_score_is_clamped() -> None:
    assert (
        policy.decide(advisory=None, stack_matches=(), enrichment=enrichment(95), profile_boost=50).priority
        is Priority.P0
    )
    assert (
        policy.decide(advisory=None, stack_matches=(), enrichment=enrichment(5), profile_boost=-50).priority
        is Priority.P3
    )


def test_thresholds_are_configurable() -> None:
    strict = PriorityPolicy(Thresholds(p0=99, p1=95, p2=90))
    assert strict.decide(advisory=None, stack_matches=(), enrichment=enrichment(80)).priority is Priority.P3


def test_advisory_without_identifiers_names_the_package() -> None:
    bare = Advisory(Severity.CRITICAL, "django", "pypi")
    assert "advisory django" in policy.decide(advisory=bare, stack_matches=DJANGO, enrichment=None).reason


def test_enrichment_rejects_invalid_values() -> None:
    with pytest.raises(ValueError, match="score"):
        Enrichment("s", "c", (), 101, action_needed=False, reason="r")
    with pytest.raises(ValueError, match="tags"):
        Enrichment("s", "c", ("a", "b", "c", "d", "e", "f"), 10, action_needed=False, reason="r")


def test_alert_on_a_watched_repository_counts_as_using_it() -> None:
    watched = Advisory(Severity.HIGH, "cryptography", "pip", identifiers=("GHSA-1",), watched=True)
    decision = policy.decide(advisory=watched, stack_matches=(), enrichment=enrichment(5))
    assert decision.priority is Priority.P1
    assert "in a repository you watch" in decision.reason


def test_critical_alert_on_a_watched_repository_is_p0() -> None:
    watched = Advisory(Severity.CRITICAL, "x", "pip", watched=True)
    assert policy.decide(advisory=watched, stack_matches=(), enrichment=None).priority is Priority.P0


def test_moderate_alert_on_a_watched_repository_has_no_floor() -> None:
    watched = Advisory(Severity.MODERATE, "x", "pip", watched=True)
    assert (
        policy.decide(advisory=watched, stack_matches=(), enrichment=enrichment(10)).priority is Priority.P3
    )
