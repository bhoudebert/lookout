# How it learns your taste

Lookout watches what you do:

| Action            | Teaches                |
| ----------------- | ---------------------- |
| Star, done        | strongly: more of this |
| Open (first time) | mildly: more of this   |
| Dismiss           | less of this           |
| Snooze            | nothing                |

It learns weights for **sources, authors, categories, kinds and tags**. Older actions count less (half-life of 30 days by default), and nothing is learnt until you have acted at least five times.

## What it changes

Items are ordered by priority first, then by model score plus a **bounded** adjustment of at most 20 points from your profile. The adjustment only orders items inside a priority: a P0 stays P0 even if you dismissed everything from its source.

## Why this rank

Open an item in the dashboard, or run `lookout explain <id>`:

```
P1 (this week): model score 85: You write Python.
model score 85
your profile moves it +16 inside its priority
  +16 kind:release
```

## Starting over

`lookout forget` (or `DELETE /api/profile`) resets what was learnt. Items and their states stay.
