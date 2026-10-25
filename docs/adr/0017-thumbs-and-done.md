# 0017. Thumbs for taste, Done to clear

- Status: accepted
- Date: 2026-10-25
- Supersedes: the dismiss part of 0011

## Context

Done and Dismiss both took an item out of the inbox and differed only in what they taught the profile (done: more like
this, dismiss: less). Users could not tell them apart, and the one that mattered (saying "I like / do not like this")
was entangled with clearing the screen. Clearing a backlog by dismissing taught the profile that the user disliked
everything. After Done the detail panel also stayed on the finished item, so the action seemed to do nothing.

## Decision

- **Clearing and taste are separate.** `Done` only takes an item out of the inbox ("discard") and teaches nothing.
  There is no `dismissed` state any more.
- **A rating** is a property of the item: up (👍), down (👎) or none, set and cleared by the same button. It teaches the
  profile (weight +3 or -3, decaying with the item's `rated_at`), whatever the item's state, and does not remove the item.
- Star keeps meaning "keep this" and still teaches; open still teaches mildly; snooze teaches nothing.
- The profile is learnt from the signals (open, star, snooze) **and from the ratings stored on items**, so changing or
  clearing a rating changes what is learnt, with no compensating events.
- After Done the dashboard closes the detail panel and moves to the next item.
- **Migration.** Dismissed items become done. The old done signals become an up rating and the old dismiss signals a down
  rating, on their items, at the time of the signal (the latest one wins); those signals are then deleted. What the
  profile had learnt is preserved. Items cleared in bulk (which recorded no signal) get no rating.

## Consequences

Two buttons mean taste, one means clear; tidying never distorts the profile. Rating is the input the later work needs
(similar rated items for the model, direct priority overrides). The API loses the `dismiss` action and the `dismissed`
state, and gains `POST /api/items/{id}/rating`.

## Alternatives considered

Keeping Dismiss as "done and dislike": a thumb down plus Done does the same in two clicks and keeps clearing neutral.
Recording ratings as events: changing a rating would need compensating events; a stored rating is the single source.
