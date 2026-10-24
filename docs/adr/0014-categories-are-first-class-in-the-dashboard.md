# 0014. Categories get their own page, editable kinds, and filing existing items again

- Status: accepted
- Date: 2026-10-24

## Context

Channels existed but were hidden at the bottom of the Sources page, with only `Other` on a fresh install, so nothing
invited the user to define any. The user thinks of them as categories, wants to define them in the dashboard and
have sources and the model file items into the right ones, and expects that to include what is already in the inbox.

## Decision

- The dashboard says **category** where the code says channel (ADR 0012), and has a page of its own, next to the
  inbox, listing each category with its description, how many items it holds and which sources feed it, with
  one-click suggestions to start from.
- **Kinds** (what an item is) are stored and edited like categories; `other` always exists. The model's answer is
  matched ignoring case against the stored list at the time it is asked.
- **Filing existing items again** is an explicit action: an item whose sources allow exactly one category is filed
  there by rule; an item sitting in `Other` whose sources allow several is queued to be read again by the model at the
  next run. Nothing is deleted, and the model budget still applies.
- While every item is in `Other`, the inbox says so and links to the page.

## Consequences

Defining categories becomes the first thing a new user can see and do. Items already in the inbox follow without
manual work. The cost of re-reading is bounded by the daily call limit and happens only when asked.

## Alternatives considered

Renaming `channel` to `category` in the code and API: churn for no user benefit, and `category` was the old name of
what is now `kind`. Re-filing automatically whenever a category is added: surprising, and spends model calls unasked.
