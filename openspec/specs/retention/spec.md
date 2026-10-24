# Retention Specification (retention)

## Purpose

Keep the inbox a working set: old entries stay out, untouched items expire, and nothing is deleted (ADR 0016).

## Requirements

### Requirement: Freshness at ingestion

Every source SHALL have `max_age_days` (a whole number, default 30; 0 means no limit). An entry published more than that
long ago SHALL NOT be stored. An entry without a publication date SHALL be stored. The setting SHALL be validated like
the other settings, in the file and in the form.

#### Scenario: A feed that serves its archive

- **WHEN** a feed returns 25 entries, 20 of them published over 30 days ago
- **THEN** 5 items are stored, and raising the source's `max_age_days` brings the others in at the next run

### Requirement: Rules and age

The floors of the priority policy SHALL apply only to items published within `rules_window_days` (default 30) of now,
or without a date. Older items are ranked by the model's score alone.

#### Scenario: An old critical advisory

- **WHEN** an item published 200 days ago carries a critical advisory on a package in the stack
- **THEN** it has no P0 floor

### Requirement: Expiry

An item in the state `new` or `seen`, not starred, SHALL move to the state `expired` when its age passes the limit of its
priority: P3 7 days, P2 14, P1 30 and P0 never by default, set by `retention.expire_after_days`. Age is counted from the
publication date, else from when the item was stored. Expiry SHALL run at every run and at startup, SHALL record no
signal, and SHALL never touch `done`, `dismissed`, `snoozed` or starred items.

#### Scenario: A quiet fortnight

- **WHEN** a P3 item has been new for 8 days
- **THEN** it is expired, absent from the inbox, present in the `expired` view, and the profile is unchanged

### Requirement: Restoring

An expired item SHALL be restorable by reopening it, which returns it to `seen`. Bulk actions SHALL work on expired
items.
