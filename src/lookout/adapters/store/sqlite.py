"""SQLite item repository with versioned migrations (ADR 0004)."""

import json
import shutil
import sqlite3
import threading
from collections.abc import Callable, Sequence
from datetime import UTC, datetime
from pathlib import Path

from lookout.adapters.store.codec import decode, encode
from lookout.application.ports import InboxQuery, Order, Page
from lookout.application.ports_sources import SourceStatus
from lookout.domain.channel import SEP, Channel
from lookout.domain.item import Item
from lookout.domain.priority import Priority
from lookout.domain.profile import Signal, SignalKind
from lookout.domain.source import SourceDef


class SchemaTooNewError(Exception):
    """The database was written by a newer Lookout."""


def migrate_v1(db: sqlite3.Connection) -> None:
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
            pending INTEGER NOT NULL,
            published_at TEXT NOT NULL,
            snoozed_until TEXT,
            data TEXT NOT NULL
        )
        """
    )
    db.execute("CREATE INDEX items_inbox ON items (state, priority, rank DESC, published_at DESC)")
    db.execute("CREATE INDEX items_pending ON items (pending, priority)")
    db.execute(
        """
        CREATE TABLE sources (
            name TEXT PRIMARY KEY,
            last_run TEXT,
            last_error TEXT,
            failures INTEGER NOT NULL,
            next_attempt TEXT,
            items_seen INTEGER NOT NULL,
            disabled INTEGER NOT NULL DEFAULT 0
        )
        """
    )
    db.execute("CREATE TABLE usage (day TEXT PRIMARY KEY, calls INTEGER NOT NULL)")
    db.execute(
        """
        CREATE TABLE signals (
            id INTEGER PRIMARY KEY, item_id TEXT NOT NULL, kind TEXT NOT NULL, at TEXT NOT NULL
        )
        """
    )


_ORDER = "priority, rank DESC, published_at DESC"
_NEWEST_FIRST = "published_at DESC, id"
# The same order as _ORDER, written out: a query built from parts looks like an injection to the linter.
_PENDING = (
    "SELECT data FROM items WHERE pending = 1 AND state IN ('new', 'seen', 'snoozed')"
    " ORDER BY priority, rank DESC, published_at DESC"
)


def migrate_v2(db: sqlite3.Connection) -> None:
    """Channels and authors (ADR 0012): the category becomes the kind; items gain a channel and an author."""
    db.execute("ALTER TABLE items RENAME COLUMN category TO kind")
    db.execute("ALTER TABLE items ADD COLUMN channel TEXT NOT NULL DEFAULT 'Other'")
    db.execute("ALTER TABLE items ADD COLUMN author TEXT NOT NULL DEFAULT ''")
    db.execute("CREATE INDEX items_channel ON items (channel)")


def migrate_v3(db: sqlite3.Connection) -> None:
    """Sources and channels the user manages (ADR 0013)."""
    db.execute(
        """
        CREATE TABLE source_defs (
            name TEXT PRIMARY KEY COLLATE NOCASE,
            type TEXT NOT NULL,
            settings TEXT NOT NULL,
            keywords TEXT NOT NULL,
            channels TEXT NOT NULL,
            enabled INTEGER NOT NULL,
            position INTEGER NOT NULL
        )
        """
    )
    db.execute("CREATE TABLE flags (name TEXT PRIMARY KEY)")
    db.execute(
        """
        CREATE TABLE channel_defs (
            name TEXT PRIMARY KEY COLLATE NOCASE,
            description TEXT NOT NULL,
            position INTEGER NOT NULL
        )
        """
    )


def migrate_v4(db: sqlite3.Connection) -> None:
    """Kinds the user manages (ADR 0014); replaced by tags in the next step."""
    db.execute("CREATE TABLE kind_defs (name TEXT PRIMARY KEY COLLATE NOCASE, position INTEGER NOT NULL)")


def migrate_v5(db: sqlite3.Connection) -> None:
    """One hierarchical category (ADR 0015): kinds are gone; items keep theirs as tags (see the codec)."""
    db.execute("DROP TABLE kind_defs")
    db.execute("ALTER TABLE items DROP COLUMN kind")


MIGRATIONS: tuple[Callable[[sqlite3.Connection], None], ...] = (
    migrate_v1,
    migrate_v2,
    migrate_v3,
    migrate_v4,
    migrate_v5,
)


class Database:
    """One SQLite file, migrated to the current schema on open (ADR 0004)."""

    def __init__(self, path: Path | str) -> None:
        self._path = Path(path)
        self._db = sqlite3.connect(str(path), isolation_level=None, check_same_thread=False)
        self._db.row_factory = sqlite3.Row
        self._lock = threading.RLock()
        try:
            self._migrate()
        except Exception:
            self._db.close()
            raise

    def query(self, sql: str, args: Sequence[object] = ()) -> list[sqlite3.Row]:
        """Run a read and return every row; threads take turns on the shared connection."""
        with self._lock:
            return self._db.execute(sql, args).fetchall()

    def run(self, sql: str, args: Sequence[object] = ()) -> None:
        """Run a write."""
        with self._lock:
            self._db.execute(sql, args)

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


class SqliteItemRepository:
    """Items in a database."""

    def __init__(self, database: Database) -> None:
        self._db = database

    def get(self, item_id: str) -> Item | None:
        """The item with this id, or ``None``."""
        rows = self._db.query("SELECT data FROM items WHERE id = ?", (item_id,))
        return decode(rows[0]["data"]) if rows else None

    def save(self, item: Item) -> None:
        """Insert or replace an item."""
        enrichment = item.enrichment
        rank = (enrichment.score if enrichment else 0) + item.boost
        tags = " ".join((*item.feed_tags, *(enrichment.tags if enrichment else ())))
        summary = enrichment.summary if enrichment else ""
        pending = enrichment is None and not item.enrichment_failed
        self._db.run(
            """
            INSERT INTO items (id, priority, state, starred, channel, author, sources, search, rank,
                               pending, published_at, snoozed_until, data)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                priority = excluded.priority, state = excluded.state, starred = excluded.starred,
                channel = excluded.channel, author = excluded.author,
                sources = excluded.sources, search = excluded.search,
                rank = excluded.rank, pending = excluded.pending, published_at = excluded.published_at,
                snoozed_until = excluded.snoozed_until, data = excluded.data
            """,
            (
                item.id,
                int(item.priority),
                item.state.value,
                int(item.starred),
                item.channel,
                item.author,
                "|" + "|".join(item.sources) + "|",
                f"{item.title}\n{summary}\n{tags}\n{item.author}".lower(),
                rank,
                int(pending),
                item.published_at.astimezone(UTC).isoformat(),
                item.snoozed_until.astimezone(UTC).isoformat() if item.snoozed_until else None,
                encode(item),
            ),
        )

    def search(self, query: InboxQuery) -> Page:
        """Items matching the filters, most urgent first, then by score, then newest."""
        where, args = _where(query)
        order = _NEWEST_FIRST if query.order is Order.DATE else _ORDER
        total = self._db.query(f"SELECT count(*) FROM items {where}", args)[0][0]  # noqa: S608
        rows = self._db.query(
            f"SELECT data FROM items {where} ORDER BY {order} LIMIT ? OFFSET ?",  # noqa: S608
            [*args, query.limit, query.offset],
        )
        return Page(tuple(decode(r["data"]) for r in rows), int(total))

    def count_by_channel(self, query: InboxQuery) -> dict[str, int]:
        """How many items each channel holds among those ``query`` matches, so counts agree with listings."""
        where, args = _where(query)
        rows = self._db.query(f"SELECT channel, count(*) AS n FROM items {where} GROUP BY channel", args)  # noqa: S608
        return {r["channel"]: int(r["n"]) for r in rows}

    def snoozed_before(self, moment: datetime) -> tuple[Item, ...]:
        """Snoozed items whose wake-up time is at or before ``moment``."""
        rows = self._db.query(
            "SELECT data FROM items WHERE state = 'snoozed' AND snoozed_until <= ?",
            (moment.astimezone(UTC).isoformat(),),
        )
        return tuple(decode(r["data"]) for r in rows)

    def untouched_before(self, priority: Priority, moment: datetime) -> tuple[Item, ...]:
        """Unstarred new or seen items of this priority published before ``moment``."""
        rows = self._db.query(
            "SELECT data FROM items WHERE state IN ('new', 'seen') AND starred = 0 AND priority = ?"
            " AND published_at < ?",
            (int(priority), moment.astimezone(UTC).isoformat()),
        )
        return tuple(decode(r["data"]) for r in rows)

    def pending_enrichment(self) -> tuple[Item, ...]:
        """Items the model has not read yet, most urgent first.

        Only those in the inbox or on their way back to it: the model is not asked about items that are done,
        dismissed or expired, which nobody sees. Reopening one makes it eligible again.
        """
        rows = self._db.query(_PENDING)
        return tuple(decode(r["data"]) for r in rows)

    def all(self) -> tuple[Item, ...]:
        """Every stored item."""
        return tuple(decode(r["data"]) for r in self._db.query("SELECT data FROM items"))


def _where(query: InboxQuery) -> tuple[str, list[object]]:
    """The SQL conditions of a query and their arguments, shared by listings and counts."""
    clauses: list[str] = []
    args: list[object] = []
    if query.priorities:
        clauses.append(f"priority IN ({_marks(query.priorities)})")
        args.extend(int(p) for p in query.priorities)
    if query.channels:
        clauses.append(
            "(" + " OR ".join("channel = ? OR substr(channel, 1, ?) = ?" for _ in query.channels) + ")"
        )
        for path in query.channels:
            prefix = path + SEP
            args.extend((path, len(prefix), prefix))
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
    if query.published_before is not None:
        clauses.append("published_at < ?")
        args.append(query.published_before.astimezone(UTC).isoformat())
    if query.published_after is not None:
        clauses.append("published_at >= ?")
        args.append(query.published_after.astimezone(UTC).isoformat())
    return ("WHERE " + " AND ".join(clauses)) if clauses else "", args


def _marks(values: object) -> str:
    return ",".join("?" for _ in values)  # type: ignore[attr-defined]


class SqliteSourceStatusRepository:
    """Health of sources."""

    def __init__(self, database: Database) -> None:
        self._db = database

    def get(self, name: str) -> SourceStatus:
        """The status of a source; a source never run has an empty one."""
        rows = self._db.query("SELECT * FROM sources WHERE name = ?", (name,))
        if not rows:
            return SourceStatus(name)
        row = rows[0]
        return SourceStatus(
            name=name,
            last_run=_read(row["last_run"]),
            last_error=row["last_error"],
            failures=row["failures"],
            next_attempt=_read(row["next_attempt"]),
            items_seen=row["items_seen"],
        )

    def save(self, status: SourceStatus) -> None:
        """Insert or replace a status."""
        self._db.run(
            """
            INSERT INTO sources (name, last_run, last_error, failures, next_attempt, items_seen)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(name) DO UPDATE SET last_run = excluded.last_run, last_error = excluded.last_error,
                failures = excluded.failures, next_attempt = excluded.next_attempt,
                items_seen = excluded.items_seen
            """,
            (
                status.name,
                _write(status.last_run),
                status.last_error,
                status.failures,
                _write(status.next_attempt),
                status.items_seen,
            ),
        )


class SqliteUsageRepository:
    """Model calls per day."""

    def __init__(self, database: Database) -> None:
        self._db = database

    def calls_on(self, day: str) -> int:
        """Calls recorded for a UTC day (``YYYY-MM-DD``)."""
        rows = self._db.query("SELECT calls FROM usage WHERE day = ?", (day,))
        return int(rows[0]["calls"]) if rows else 0

    def record_call(self, day: str) -> None:
        """Count one call."""
        self._db.run(
            "INSERT INTO usage (day, calls) VALUES (?, 1) ON CONFLICT(day) DO UPDATE SET calls = calls + 1",
            (day,),
        )


def _write(moment: datetime | None) -> str | None:
    return moment.astimezone(UTC).isoformat() if moment else None


def _read(text: str | None) -> datetime | None:
    return datetime.fromisoformat(text) if text else None


class SqliteSignalRepository:
    """What the user did, in order."""

    def __init__(self, database: Database) -> None:
        self._db = database

    def add(self, signal: Signal) -> None:
        """Remember one action."""
        self._db.run(
            "INSERT INTO signals (item_id, kind, at) VALUES (?, ?, ?)",
            (signal.item_id, signal.kind.value, signal.at.astimezone(UTC).isoformat()),
        )

    def all(self) -> tuple[Signal, ...]:
        """Every action, oldest first."""
        rows = self._db.query("SELECT item_id, kind, at FROM signals ORDER BY id")
        return tuple(
            Signal(r["item_id"], SignalKind(r["kind"]), datetime.fromisoformat(r["at"])) for r in rows
        )

    def clear(self) -> None:
        """Forget everything the user did (the profile resets; items are untouched)."""
        self._db.run("DELETE FROM signals")


class SqliteSourceDefinitions:
    """The sources the user manages, in the order they were added."""

    def __init__(self, database: Database) -> None:
        self._db = database

    def all(self) -> tuple[SourceDef, ...]:
        """Every source."""
        rows = self._db.query("SELECT * FROM source_defs ORDER BY position")
        return tuple(
            SourceDef(
                name=r["name"],
                type=r["type"],
                settings=json.loads(r["settings"]),
                keywords=tuple(json.loads(r["keywords"])),
                channels=tuple(json.loads(r["channels"])),
                enabled=bool(r["enabled"]),
            )
            for r in rows
        )

    def save(self, source: SourceDef) -> None:
        """Insert a source, or replace the one with this name keeping its place."""
        self._db.run(
            """
            INSERT INTO source_defs (name, type, settings, keywords, channels, enabled, position)
            VALUES (?, ?, ?, ?, ?, ?, (SELECT COALESCE(MAX(position), 0) + 1 FROM source_defs))
            ON CONFLICT(name) DO UPDATE SET type = excluded.type, settings = excluded.settings,
                keywords = excluded.keywords, channels = excluded.channels, enabled = excluded.enabled
            """,
            (
                source.name,
                source.type,
                json.dumps(source.settings, sort_keys=True),
                json.dumps(list(source.keywords)),
                json.dumps(list(source.channels)),
                int(source.enabled),
            ),
        )

    def delete(self, name: str) -> None:
        """Forget a source and how its runs went; its items stay."""
        self._db.run("DELETE FROM source_defs WHERE name = ?", (name,))
        self._db.run("DELETE FROM sources WHERE name = ?", (name,))


class SqliteChannelDefinitions:
    """The channels the user manages, in the order they were added."""

    def __init__(self, database: Database) -> None:
        self._db = database

    def all(self) -> tuple[Channel, ...]:
        """Every channel."""
        rows = self._db.query("SELECT name, description FROM channel_defs ORDER BY position")
        return tuple(Channel(r["name"], r["description"]) for r in rows)

    def save(self, channel: Channel) -> None:
        """Insert a channel, or change the description of the one with this name."""
        self._db.run(
            """
            INSERT INTO channel_defs (name, description, position)
            VALUES (?, ?, (SELECT COALESCE(MAX(position), 0) + 1 FROM channel_defs))
            ON CONFLICT(name) DO UPDATE SET description = excluded.description
            """,
            (channel.name, channel.description),
        )

    def rename(self, old: str, new: str) -> None:
        """Give a channel another path, keeping its description and its place."""
        self._db.run("UPDATE channel_defs SET name = ? WHERE name = ?", (new, old))

    def delete(self, name: str) -> None:
        """Forget a channel; items already filed in it keep its name."""
        self._db.run("DELETE FROM channel_defs WHERE name = ?", (name,))


class SqliteFlags:
    """Things that happened once, such as the first seeding of sources from the file."""

    def __init__(self, database: Database) -> None:
        self._db = database

    def is_set(self, name: str) -> bool:
        """Whether ``name`` has been set."""
        return bool(self._db.query("SELECT 1 FROM flags WHERE name = ?", (name,)))

    def set(self, name: str) -> None:
        """Remember that ``name`` happened."""
        self._db.run("INSERT OR IGNORE INTO flags (name) VALUES (?)", (name,))
