# 0016. Keep the inbox small: freshness, expiry, two orders, paging

- Status: accepted
- Date: 2026-10-25

## Context

Lookout ingests everything a feed returns and keeps it forever. A feed that serves its archive, or a few weeks of
neglect, buries the inbox: one user had 2329 items in one category, the dashboard showed the first 100 with no way to
reach the rest, ordering ignored age, and a 300-day-old release still carried a P0 rule floor. Triage by priority is the
right default, but the user also wants to keep up with what is new, in order.

## Decision

- **Freshness at the door.** Every source has `max_age_days` (default 30, 0 for no limit). Entries published earlier are
  not stored; entries without a date are kept. The rule floors of the priority policy only apply to items published
  within `rules_window_days` (default 30), so an old advisory cannot demand action today.
- **Expiry.** A new state `expired` is reached only by the system. Items still `new` or `seen` after a time that depends
  on their priority (default P3 7 days, P2 14, P1 30, P0 never; P4 when it exists 3) move to it. It is not a signal: the
  profile never learns from it. An expired item can be restored (it returns to `seen`) and is found in the `expired`
  view. Starred items never expire. The age is counted from the publication date, or from when the item was stored when
  there is none.
- **Two orders** on the same list: `priority` (band, then profile, then date; the triage default) and `date` (newest
  first, the priority only shown). The dashboard calls them Triage and Latest.
- **Paging everywhere.** Pages of 50, "Load more", and the real total.
- **Age as a filter** (`older_than_days`, `newer_than_days`) and **bulk actions on a filter**: apply an action to
  everything a filter matches, with a dry run that counts and samples first.
- The chat box that is planned (a later ADR) turns a sentence into these same filters and bulk actions; it does not get
  powers of its own.

## Consequences

The inbox stays a working set. Nothing is deleted: expiry and the age limit are reversible (expired items stay, and a
source can be given a longer `max_age_days` to bring older entries in at the next run). The policy defaults are
opinions; they are configurable (`retention` in the file now, the dashboard later).

## Alternatives considered

Deleting old items: irreversible and loses history that personalization may still use. Expiry as dismissal: it would
teach the profile that the user dislikes everything they were too busy to read. Ordering by age only: it buries the
critical advisory under a day's chatter, which is why the two orders are separate.
