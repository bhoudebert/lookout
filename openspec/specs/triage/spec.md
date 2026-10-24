# Triage Specification (triage)

## Purpose

Let the user work an inbox: see, act, defer, discard.

## Requirements

### Requirement: States

An item SHALL be in one state: `new`, `seen`, `done`, `snoozed` (with a wake time) or `dismissed`. An independent star
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
state, star and text, ordered by priority band, then personal score, then recency. The result SHALL be paginated.

### Requirement: Bulk actions

The user SHALL be able to apply a transition to several items at once, and to mark everything below a priority as
`seen`.

### Requirement: Every entry point

All transitions SHALL be reachable from the HTTP API and the CLI.
