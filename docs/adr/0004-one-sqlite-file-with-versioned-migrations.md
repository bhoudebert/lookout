# 0004. One SQLite file with versioned migrations

- Status: accepted
- Date: 2026-10-24

## Context

Lookout runs on a laptop, a home server or a small VPS, for one person. It stores items, states, feedback, the
learned profile and cached embeddings.

## Decision

One SQLite file through the standard library `sqlite3`, behind `ItemRepository`. The schema version is stored in the
file; pending migration steps run once each, in order, each in a transaction with its version bump; a backup copy is
written before the first pending step; a file newer than the app is refused unchanged. JSON columns hold nested data.

## Consequences

No server, backups are a file copy, tests use a real temp file. One writer at a time and no multi-user story, which is
not needed now. No ORM: SQL is explicit, typed at the adapter edge.

## Alternatives considered

PostgreSQL: right for many users, overkill here. SQLAlchemy: adds a layer the domain does not need.
