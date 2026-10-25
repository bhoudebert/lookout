# How it learns your taste

Lookout watches what you do:

| Action                   | Teaches                |
| ------------------------ | ---------------------- |
| Thumbs up, star          | strongly: more of this |
| Thumbs down              | strongly: less of this |
| Open (first time)        | mildly: more of this   |
| **Done**, snooze, expiry | nothing                |

**Done only clears.** It takes the item out of the inbox and says nothing about your taste, so tidying a backlog never teaches Lookout that you dislike a source. Taste is said with the **thumbs** on each item: the same thumb again clears it, and changing or clearing a rating changes what Lookout has learnt. A rating never removes the item from the inbox.

It learns weights for **authors, categories (and the ones above them) and tags**, and for **sources** from what you open and star. Older actions count less (half-life of 30 days by default), and nothing is learnt until you have acted at least five times.

**A thumb judges the content, never the source.** Rating one story down does not demote the subreddit or the blog it came from; it teaches about its author, category and tags. And when the model reads a new item, it is shown the titles and tags of what you rated most recently (up to five liked and five disliked) as samples of your taste. That is how "a guy had a small moto crash, I don't care" lowers the next story like it, whichever source it comes from. Thumb down a few of them and it gets stronger.

## What it changes

Items are ordered by priority first, then by model score plus a **bounded** adjustment of at most 20 points from your profile. The adjustment only orders items inside a priority: a P0 stays P0 even if you rated everything from its source down.

## Why this rank

Open an item in the dashboard, or run `lookout explain <id>`:

```
P1 (this week): model score 85: You write Python.
model score 85
your profile moves it +16 inside its priority
  +16 category:Dev > Rust
```

## Starting over

`lookout forget` (or `DELETE /api/profile`) resets what was learnt. Items and their states stay.
