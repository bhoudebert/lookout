"""Scenarios of openspec/specs/enrichment."""

from tests.support import FixedClock, ScriptedEnricher, database, enrichment, make_item

from lookout.adapters.store.sqlite import SqliteItemRepository, SqliteUsageRepository
from lookout.application.enrich import Enrich
from lookout.application.ports_sources import EnrichmentError
from lookout.domain.advisory import Advisory
from lookout.domain.policy import PriorityPolicy
from lookout.domain.priority import Priority
from lookout.domain.severity import Severity


def build(
    enricher: ScriptedEnricher, limit: int = 10
) -> tuple[Enrich, SqliteItemRepository, SqliteUsageRepository, FixedClock]:
    db = database()
    items, usage, clock = SqliteItemRepository(db), SqliteUsageRepository(db), FixedClock()
    return Enrich(items, enricher, usage, clock, PriorityPolicy(), daily_limit=limit), items, usage, clock


def test_reading_sets_the_summary_and_a_priority_from_the_score() -> None:
    enrich, items, _, _ = build(ScriptedEnricher({"Big news": enrichment(92, summary="Huge")}))
    item = make_item(title="Big news")
    items.save(item)
    report = enrich.run()
    stored = items.get(item.id)
    assert stored is not None
    assert (report.enriched, stored.priority) == (1, Priority.P0)
    assert stored.enrichment is not None
    assert stored.enrichment.summary == "Huge"
    assert "score 92" in stored.priority_reason


def test_model_cannot_lower_a_rule_floor() -> None:
    advisory = Advisory(Severity.CRITICAL, "django", "pypi", identifiers=("CVE-1",))
    enrich, items, _, _ = build(ScriptedEnricher({"Django flaw": enrichment(3)}))
    item = make_item(title="Django flaw", advisory=advisory).assessed(Priority.P0, "rule", ("django",))
    items.save(item)
    enrich.run()
    stored = items.get(item.id)
    assert stored is not None
    assert (stored.priority, stored.stack_matches) == (Priority.P0, ("django",))
    assert stored.priority_reason.startswith("rule:")


def test_model_failing_keeps_the_item_flagged_and_is_not_retried() -> None:
    enricher = ScriptedEnricher({"Broken": EnrichmentError("no valid answer")})
    enrich, items, _, _ = build(enricher)
    item = make_item(title="Broken")
    items.save(item)
    assert enrich.run().failed == 1
    stored = items.get(item.id)
    assert stored is not None
    assert (stored.enrichment_failed, stored.enrichment) == (True, None)
    enrich.run()
    assert enricher.asked == ["Broken"]


def test_budget_exhausted_leaves_items_waiting_with_their_rule_priority() -> None:
    enricher = ScriptedEnricher()
    enrich, items, usage, clock = build(enricher, limit=1)
    advisory = Advisory(Severity.CRITICAL, "django", "pypi")
    urgent = make_item("https://a.test/urgent", title="Urgent", advisory=advisory).assessed(
        Priority.P0, "rule", ("django",)
    )
    other = make_item("https://a.test/other", title="Other")
    items.save(other)
    items.save(urgent)

    report = enrich.run()
    assert (report.enriched, report.waiting) == (1, 1)
    assert enricher.asked == ["Urgent"]
    waiting = items.get(other.id)
    assert waiting is not None
    assert waiting.enrichment is None
    assert usage.calls_on("2026-10-24") == 1

    clock.advance(days=1)
    assert enrich.run().enriched == 1
    assert enricher.asked == ["Urgent", "Other"]


def test_nothing_pending_does_nothing() -> None:
    enrich, _, usage, _ = build(ScriptedEnricher())
    assert enrich.run().enriched == 0
    assert usage.calls_on("2026-10-24") == 0
