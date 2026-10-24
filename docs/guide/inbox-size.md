# Keeping the inbox small

An inbox is a working set, not an archive. Lookout keeps it small in three ways, and **deletes nothing**.

## Old entries stay out

Every source has `max_age_days` (30 by default, `0` for no limit). An entry published before that is not stored; an entry
with no date is kept. Set it in the source form ("Ignore entries older than") or in the file:

```yaml
sources:
  - name: ai blog
    type: rss
    url: https://example.com/feed.xml
    max_age_days: 14
```

A feed that serves its whole archive no longer buries you the first time you add it. Raise the limit to bring older
entries in at the next run; note that they will then expire at once if they are older than the limit of their priority
(below), and wait in the **Expired** view.

Rule floors also respect age: an advisory published more than `rules_window_days` (30) ago gets no P0 or P1 floor, so a
300-day-old release cannot ask you to act today. The model's score still ranks it.

## Untouched items expire

An item you never opened, finished, dismissed, snoozed or starred moves to the **Expired** view after a time that depends
on how urgent it was:

| Priority | Expires after |
| -------- | ------------- |
| P0       | never         |
| P1       | 30 days       |
| P2       | 14 days       |
| P3       | 7 days        |

Change it under `retention.expire_after_days` in the [configuration](/configuration) (`0` means never). The age counts
from the publication date. Expiry happens at every run and when Lookout starts.

Expiry is **not** a signal. Lookout does not learn from it, because an item you were too busy to read says nothing about
your taste. Open an expired item (or choose Reopen) and it comes back as seen.

## Two orders, and pages

The list can be ordered two ways, kept in the address so you can bookmark either:

- **Triage**: priority first, then your profile, then date. The default.
- **Latest**: newest first, whatever the priority, with a divider before what arrived since your last visit.

Either way the list shows 50 items and a **Load more** button, with the real total ("50 of 2329").

## Clearing a backlog

Filter to what you want (a category, a source, "older than 2 weeks") and use **Mark all N as ...**. Lookout counts and shows
a sample first, asks you to confirm, and offers Undo afterwards.
