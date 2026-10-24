# Triage Specification (triage)

## Purpose

Let the user work an inbox: see, act, defer, discard.

## Requirements

### Requirement: States

An item SHALL be in one state: `new`, `seen`, `done`, `snoozed` (with a wake time), `dismissed` or `expired` (reached by
the system only, see retention). An independent star
flag SHALL be settable in any state. Opening an item moves `new` to `seen`.

#### Scenario: Open an item

- **WHEN** the user opens a new item
- **THEN** it becomes `seen` and a `seen` signal is recorded

### Requirement: Transitions

`done`, `dismissed` and `snoozed` SHALL be reachable from any other state, and reopening SHALL return the item to
`seen`. A snoozed item SHALL return to `new` when its wake time passes, as a result of the next scheduler tick or inbox
query.

#### Scenario: Snooze wakes

- **WHEN** an item snoozed until 09:00 is listed at 09:01
- **THEN** it appears as `new` in the inbox

### Requirement: Inbox query

The inbox SHALL list items not `done`, not `dismissed` and not snoozed, filterable by priority, category, source,
state, star, text and age (`older_than_days`, `newer_than_days`). It SHALL be orderable by `priority` (band, then personal
score, then recency; the default) or by `date` (newest first). The result SHALL be paginated and say the real total.

### Requirement: Bulk actions

The user SHALL be able to apply a transition to several items at once, and to mark everything below a priority as
`seen`.

### Requirement: Bulk actions on a filter

The user SHALL be able to apply a transition to everything a filter matches, and SHALL be able to ask first how many items
that is and see a sample, without changing anything.

#### Scenario: Clearing a backlog

- **WHEN** the user asks to mark `AI` older than 14 days as done, as a dry run, then for real
- **THEN** the dry run reports the count and a sample and changes nothing, the real run changes exactly those items, and
  the whole action can be undone

### Requirement: Every entry point

All transitions SHALL be reachable from the HTTP API and the CLI.
