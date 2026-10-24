"""Demo data: a believable inbox for trying the dashboard and for end-to-end tests."""

from datetime import datetime, timedelta

from lookout.application.ports import ItemRepository
from lookout.domain.advisory import Advisory
from lookout.domain.channel import OTHER
from lookout.domain.enrichment import Enrichment
from lookout.domain.item import Item, item_id
from lookout.domain.policy import PriorityPolicy
from lookout.domain.severity import Severity
from lookout.domain.stack import Stack

# title, url, source, kind, channel, author, tags, score, summary, advisory
_DEMO: tuple[tuple[str, str, str, str, str, str, tuple[str, ...], int, str, Advisory | None], ...] = (
    (
        "Django security releases 5.2.9 and 5.1.15 fix a SQL injection",
        "https://example.test/django-sqli",
        "osv",
        "security",
        "Security",
        "Django Security Team",
        ("django", "sql-injection"),
        96,
        "Critical SQL injection in the ORM's JSON field lookups. Upgrade to 5.2.9 or 5.1.15.",
        Advisory(Severity.CRITICAL, "django", "pypi", identifiers=("CVE-2026-1234",)),
    ),
    (
        "Dependabot: bump cryptography from 43.0.0 to 44.0.1 in api-service",
        "https://example.test/dependabot-cryptography",
        "github:acme/api-service",
        "security",
        "Security",
        "dependabot[bot]",
        ("cryptography", "python"),
        78,
        "High severity issue in cryptography's PKCS12 parsing. A grouped PR is ready.",
        Advisory(Severity.HIGH, "cryptography", "pypi", identifiers=("GHSA-xxxx",)),
    ),
    (
        "React 20 release candidate: new compiler enabled by default",
        "https://example.test/react-20-rc",
        "react-blog",
        "release",
        "Web",
        "The React Team",
        ("react", "compiler"),
        72,
        "The React compiler becomes the default; class components keep working. Migration guide published.",
        None,
    ),
    (
        "PostgreSQL 18 beta improves logical replication",
        "https://example.test/postgres-18",
        "hn",
        "release",
        "Other",
        "PostgreSQL Global Development Group",
        ("postgresql", "replication"),
        55,
        "Parallel apply for logical replication and faster VACUUM.",
        None,
    ),
    (
        "Show HN: a tiny Rust feed reader",
        "https://example.test/rust-reader",
        "hn",
        "announcement",
        "Rust",
        "ferris",
        ("rust", "rss"),
        41,
        "A single-binary RSS reader written in Rust with SQLite storage.",
        None,
    ),
    (
        "The state of AI coding assistants in 2026",
        "https://example.test/ai-state",
        "reddit:programming",
        "research",
        "AI",
        "Jane Doe",
        ("llm", "coding"),
        30,
        "A survey of assistants, their benchmarks and adoption in teams.",
        None,
    ),
)


def seed_demo(
    items: ItemRepository,
    now: datetime,
    policy: PriorityPolicy,
    stack: Stack,
    channels: tuple[str, ...] = (),
) -> int:
    """Store the demo items (idempotent), prioritised by the real policy; returns how many were added.

    Each goes in its demo channel when the user has declared it, else in ``Other``.
    """
    declared = {c.lower(): c for c in channels}
    added = 0
    for number, (title, url, source, kind, channel, author, tags, score, summary, advisory) in enumerate(
        _DEMO
    ):
        ident = item_id(url)
        if items.get(ident) is not None:
            continue
        item = Item(
            id=ident,
            url=url,
            title=title,
            body=summary,
            published_at=now - timedelta(hours=2 * number + 1),
            sources=(source,),
            advisory=advisory,
            author=author,
            feed_tags=tags[:1],
        )
        matches = stack.match(f"{title}\n{summary}", advisory)
        reading = Enrichment(
            summary,
            kind,
            declared.get(channel.lower(), OTHER),
            tags,
            score,
            action_needed=score >= 70,
            reason="demo data",
        )
        decision = policy.decide(advisory=advisory, stack_matches=matches, enrichment=reading)
        items.save(item.enriched(reading).assessed(decision.priority, decision.reason, matches))
        added += 1
    return added
