# 0011. Item lifecycle and priority model

- Status: accepted
- Date: 2026-10-24

## Context

Lookout is a triage inbox for daily work, not a daily digest: an item is something to see, then maybe act on.

## Decision

States: `new → seen → done`, or `snoozed(until)` (returns to `new` at that time) (`dismissed` was folded into `done` by ADR 0017); `starred` is an
independent flag. Transitions are enforced by the domain; done and dismissed are reversible by reopening. Priority is
P0 (act today), P1 (this week), P2 (read when free), P3 (background), plus an `action_needed` flag. Categories are an
open list configured by the user with a built-in default set (security, release, breaking-change, tooling, ai,
industry, other). The inbox sorts by priority band, then by personal score.

## Consequences

The inbox answers "what needs me now". Feedback signals (seen, done, star, dismiss) are all stored for learning.

## Alternatives considered

Read/unread only: no way to express "handled". Numeric priority only: hard to scan and to attach floors to.
