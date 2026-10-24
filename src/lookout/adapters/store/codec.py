"""Item <-> JSON, the shape stored in the ``data`` column. Versioned by the migrations, not by this file."""

import json
from datetime import UTC, datetime
from typing import Any, cast

from lookout.domain.advisory import Advisory
from lookout.domain.enrichment import Enrichment
from lookout.domain.item import Item
from lookout.domain.priority import Priority
from lookout.domain.severity import Severity
from lookout.domain.state import State


def encode(item: Item) -> str:
    """Serialise an item."""
    return json.dumps(
        {
            "id": item.id,
            "url": item.url,
            "title": item.title,
            "body": item.body,
            "published_at": _dt(item.published_at),
            "sources": list(item.sources),
            "advisory": _advisory(item.advisory),
            "enrichment": _enrichment(item.enrichment),
            "enrichment_failed": item.enrichment_failed,
            "stack_matches": list(item.stack_matches),
            "priority": int(item.priority),
            "priority_reason": item.priority_reason,
            "state": item.state.value,
            "snoozed_until": _dt(item.snoozed_until) if item.snoozed_until else None,
            "starred": item.starred,
            "boost": item.boost,
            "extra": item.extra,
        },
        separators=(",", ":"),
    )


def decode(text: str) -> Item:
    """Read an item back."""
    raw = cast("dict[str, Any]", json.loads(text))
    return Item(
        id=raw["id"],
        url=raw["url"],
        title=raw["title"],
        body=raw["body"],
        published_at=datetime.fromisoformat(raw["published_at"]),
        sources=tuple(raw["sources"]),
        advisory=_read_advisory(raw["advisory"]),
        enrichment=_read_enrichment(raw["enrichment"]),
        enrichment_failed=raw["enrichment_failed"],
        stack_matches=tuple(raw["stack_matches"]),
        priority=Priority(raw["priority"]),
        priority_reason=raw["priority_reason"],
        state=State(raw["state"]),
        snoozed_until=datetime.fromisoformat(raw["snoozed_until"]) if raw["snoozed_until"] else None,
        starred=raw["starred"],
        boost=raw["boost"],
        extra=raw["extra"],
    )


def _dt(moment: datetime) -> str:
    return moment.astimezone(UTC).isoformat()


def _advisory(advisory: Advisory | None) -> dict[str, Any] | None:
    if advisory is None:
        return None
    return {
        "severity": int(advisory.severity),
        "package": advisory.package,
        "ecosystem": advisory.ecosystem,
        "known_exploited": advisory.known_exploited,
        "watched": advisory.watched,
        "identifiers": list(advisory.identifiers),
    }


def _read_advisory(raw: dict[str, Any] | None) -> Advisory | None:
    if raw is None:
        return None
    return Advisory(
        severity=Severity(raw["severity"]),
        package=raw["package"],
        ecosystem=raw["ecosystem"],
        known_exploited=raw["known_exploited"],
        watched=raw.get("watched", False),
        identifiers=tuple(raw["identifiers"]),
    )


def _enrichment(enrichment: Enrichment | None) -> dict[str, Any] | None:
    if enrichment is None:
        return None
    return {
        "summary": enrichment.summary,
        "category": enrichment.category,
        "tags": list(enrichment.tags),
        "score": enrichment.score,
        "action_needed": enrichment.action_needed,
        "reason": enrichment.reason,
    }


def _read_enrichment(raw: dict[str, Any] | None) -> Enrichment | None:
    if raw is None:
        return None
    return Enrichment(
        summary=raw["summary"],
        category=raw["category"],
        tags=tuple(raw["tags"]),
        score=raw["score"],
        action_needed=raw["action_needed"],
        reason=raw["reason"],
    )
