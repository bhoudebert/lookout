"""SQLite item repository with versioned migrations (ADR 0004)."""

import shutil
import sqlite3
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path

from lookout.adapters.store.codec import decode, encode
from lookout.application.ports import InboxQuery, Page
from lookout.domain.item import Item


class SchemaTooNewError(Exception):
    """The database was written by a newer Lookout."""


def _v1(db: sqlite3.Connection) -> None:
    db.execute(
        """
        CREATE TABLE items (
            id TEXT PRIMARY KEY,
            priority INTEGER NOT NULL,
            state TEXT NOT NULL,
            starred INTEGER NOT NULL,
            category TEXT NOT NULL,
            sources TEXT NOT NULL,
            search TEXT NOT NULL,
            rank INTEGER NOT NULL,
            published_at TEXT NOT NULL,
            snoozed_until TEXT,
            data TEXT NOT NULL
        )
        """
    )
    db.execute("CREATE INDEX items_inbox ON items (state, priority, rank DESC, published_at DESC)")


_ORDER = "priority, rank DESC, published_at DESC"

MIGRATIONS: tuple[Callable[[sqlite3.Connection], None], ...] = (_v1,)


class SqliteItemRepository:
    """Items in one SQLite file. Each public method is one transaction."""

    def __init__(self, path: Path | str) -> None:
        self._path = Path(path)
        self._db = sqlite3.connect(str(path), isolation_level=None)
        self._db.row_factory = sqlite3.Row
        self._migrate()

    def close(self) -> None:
        """Close the connection."""
        self._db.close()

    # Migrations -----------------------------------------------------------------------------------------

    def _migrate(self) -> None:
        current = int(self._db.execute("PRAGMA user_version").fetchone()[0])
        target = len(MIGRATIONS)
        if current > target:
            msg = f"database is at schema version {current}, this Lookout knows up to {target}"
            raise SchemaTooNewError(msg)
        if 0 < current < target:
            self._backup(current)
        for version in range(current, target):
            self._db.execute("BEGIN")
            try:
                MIGRATIONS[version](self._db)
                self._db.execute(f"PRAGMA user_version = {version + 1}")
            except Exception:
                self._db.execute("ROLLBACK")
                raise
            self._db.execute("COMMIT")

    def _backup(self, version: int) -> None:
        shutil.copyfile(self._path, self._path.with_name(f"{self._path.name}.bak-v{version}"))

    # Repository -----------------------------------------------------------------------------------------

    def get(self, item_id: str) -> Item | None:
        """The item with this id, or ``None``."""
        row = self._db.execute("SELECT data FROM items WHERE id = ?", (item_id,)).fetchone()
        return decode(row["data"]) if row else None

    def save(self, item: Item) -> None:
        """Insert or replace an item."""
        enrichment = item.enrichment
        rank = enrichment.score if enrichment else 0
        category = enrichment.category if enrichment else ""
        tags = " ".join(enrichment.tags) if enrichment else ""
        summary = enrichment.summary if enrichment else ""
        self._db.execute(
            """
            INSERT INTO items (id, priority, state, starred, category, sources, search, rank,
                               published_at, snoozed_until, data)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                priority = excluded.priority, state = excluded.state, starred = excluded.starred,
                category = excluded.category, sources = excluded.sources, search = excluded.search,
                rank = excluded.rank, published_at = excluded.published_at,
                snoozed_until = excluded.snoozed_until, data = excluded.data
            """,
            (
                item.id,
                int(item.priority),
                item.state.value,
                int(item.starred),
                category,
                "|" + "|".join(item.sources) + "|",
                f"{item.title}\n{summary}\n{tags}".lower(),
                rank,
                item.published_at.astimezone(UTC).isoformat(),
                item.snoozed_until.astimezone(UTC).isoformat() if item.snoozed_until else None,
                encode(item),
            ),
        )

    def search(self, query: InboxQuery) -> Page:
        """Items matching the filters, most urgent first, then by score, then newest."""
        clauses: list[str] = []
        args: list[object] = []
        if query.priorities:
            clauses.append(f"priority IN ({_marks(query.priorities)})")
            args.extend(int(p) for p in query.priorities)
        if query.categories:
            clauses.append(f"category IN ({_marks(query.categories)})")
            args.extend(query.categories)
        if query.states:
            clauses.append(f"state IN ({_marks(query.states)})")
            args.extend(s.value for s in query.states)
        if query.sources:
            clauses.append("(" + " OR ".join("sources LIKE ?" for _ in query.sources) + ")")
            args.extend(f"%|{name}|%" for name in query.sources)
        if query.starred is not None:
            clauses.append("starred = ?")
            args.append(int(query.starred))
        if query.text:
            clauses.append("search LIKE ?")
            args.append(f"%{query.text.lower()}%")
        where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
        total = self._db.execute(f"SELECT count(*) FROM items {where}", args).fetchone()[0]  # noqa: S608
        rows = self._db.execute(
            f"SELECT data FROM items {where} ORDER BY {_ORDER} LIMIT ? OFFSET ?",  # noqa: S608
            [*args, query.limit, query.offset],
        ).fetchall()
        return Page(tuple(decode(r["data"]) for r in rows), int(total))

    def snoozed_before(self, moment: datetime) -> tuple[Item, ...]:
        """Snoozed items whose wake-up time is at or before ``moment``."""
        rows = self._db.execute(
            "SELECT data FROM items WHERE state = 'snoozed' AND snoozed_until <= ?",
            (moment.astimezone(UTC).isoformat(),),
        ).fetchall()
        return tuple(decode(r["data"]) for r in rows)

    def all(self) -> tuple[Item, ...]:
        """Every stored item."""
        return tuple(decode(r["data"]) for r in self._db.execute("SELECT data FROM items"))


def _marks(values: object) -> str:
    return ",".join("?" for _ in values)  # type: ignore[attr-defined]
