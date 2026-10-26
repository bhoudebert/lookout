"""Item <-> JSON, the shape stored in the ``data`` column. Versioned by the migrations, not by this file."""

import json
from datetime import UTC, datetime
from typing import Any, cast

from lookout.domain.advisory import Advisory
from lookout.domain.channel import OTHER
from lookout.domain.digest import Digest, Point, Section
from lookout.domain.enrichment import MAX_TAGS, Enrichment
from lookout.domain.item import Item
from lookout.domain.priority import Priority
from lookout.domain.rating import Rating
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
            "rating": int(item.rating),
            "rated_at": _dt(item.rated_at) if item.rated_at else None,
            "boost": item.boost,
            "author": item.author,
            "channel": item.channel,
            "feed_tags": list(item.feed_tags),
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
        rating=Rating(raw.get("rating", 0)),
        rated_at=datetime.fromisoformat(raw["rated_at"]) if raw.get("rated_at") else None,
        boost=raw["boost"],
        author=raw.get("author", ""),
        channel=raw.get("channel", OTHER),
        feed_tags=tuple(raw.get("feed_tags", [])),
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
        "channel": enrichment.channel,
        "tags": list(enrichment.tags),
        "score": enrichment.score,
        "action_needed": enrichment.action_needed,
        "reason": enrichment.reason,
    }


def _read_enrichment(raw: dict[str, Any] | None) -> Enrichment | None:
    if raw is None:
        return None
    # Items read before categories were one thing carry a kind (or a category): it is kept as a tag.
    legacy = raw.get("kind") or raw.get("category")
    wanted: list[str] = [*raw["tags"], *([legacy] if legacy else [])]
    tags = tuple(dict.fromkeys(wanted))[:MAX_TAGS]
    return Enrichment(
        summary=raw["summary"],
        channel=raw.get("channel", OTHER),
        tags=tags,
        score=raw["score"],
        action_needed=raw["action_needed"],
        reason=raw["reason"],
    )


def encode_digest(digest: Digest) -> str:
    """Serialise a digest."""
    return json.dumps(
        {
            "id": digest.id,
            "created_at": _dt(digest.created_at),
            "scope": digest.scope,
            "headline": digest.headline,
            "sections": [
                {"title": s.title, "points": [{"text": p.text, "items": list(p.items)} for p in s.points]}
                for s in digest.sections
            ],
            "uncovered": list(digest.uncovered),
            "total": digest.total,
            "since": _dt(digest.since) if digest.since else None,
            "until": _dt(digest.until) if digest.until else None,
        }
    )


def decode_digest(text: str) -> Digest:
    """Read a digest back."""
    raw = cast("dict[str, Any]", json.loads(text))
    return Digest(
        id=raw["id"],
        created_at=datetime.fromisoformat(raw["created_at"]),
        scope=raw["scope"],
        headline=raw["headline"],
        sections=tuple(
            Section(s["title"], tuple(Point(p["text"], tuple(p["items"])) for p in s["points"]))
            for s in raw["sections"]
        ),
        uncovered=tuple(raw["uncovered"]),
        total=raw["total"],
        since=datetime.fromisoformat(raw["since"]) if raw.get("since") else None,
        until=datetime.fromisoformat(raw["until"]) if raw.get("until") else None,
    )
