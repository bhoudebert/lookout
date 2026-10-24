# How Lookout thinks

## Items

An **item** is one piece of content from a source: a blog post, a release, an advisory. Lookout stores each story once. The same link arriving from two sources (after removing tracking parameters) is one item that lists both sources.

Text from the internet is **data, never instructions**. Markup is stripped, sizes are bounded, and a title that says "ignore previous instructions" is stored as plain text and decides nothing.

## Reading

For each new item the model returns a summary, one category from your list, up to five tags, an importance score from 0 to 100, whether you must act, and one sentence of reasoning. The answer is validated; one invalid answer gets one repair attempt, then the item stays in the inbox, flagged as not read. Nothing is ever dropped.

A daily call limit protects a paid model. When it is spent, items wait, and the rules below still apply to them.

## Priority

| Level | Meaning        |
| ----- | -------------- |
| P0    | act today      |
| P1    | this week      |
| P2    | read when free |
| P3    | background     |

See [how priority is decided](/priorities).

## States

An item is **new**, **seen**, **done**, **snoozed** (until a time) or **dismissed**. Starring is separate and works in any state. Opening a new item makes it seen. Done, dismissed and snoozed items leave the inbox; reopening brings them back as seen. A snoozed item returns as new when its time comes.

## Your stack

The packages and tools you depend on, declared in `lookout.yaml`. Items that name them, and advisories that affect them, are matched by whole word and alias (`postgres` for `postgresql`).
