# 0015. One hierarchical category; kinds become tags

- Status: accepted
- Date: 2026-10-25
- Supersedes: the two-axis part of 0012 (channels and kinds)

## Context

ADR 0012 split an item's filing into a channel (topic) and a kind (type). In use the user found them to be the same
notion: some categories are wider than others and some nest, like Dev > Rust. Two axes made the screen and the model's
task harder, and the rating that is coming (ADR 0017) needs one clear thing to learn from.

## Decision

- There is one **category**, a path of up to four names joined by `>` (`Dev > Rust`). Each item is filed in exactly
  one, the most specific that fits. `Other` is the top-level last resort.
- Creating `Dev > Rust` creates `Dev` too. A category with subcategories cannot be deleted; one a source feeds cannot
  be deleted either.
- A source feeding a category allows that category and everything under it. It files items directly only when that is
  exactly one category with no subcategories; otherwise the model chooses among them.
- Filtering by a category includes its subcategories.
- **Kinds disappear.** What an item is (release, security, outage...) is expressed by tags, which the model already
  returns and which the article may carry. Existing kinds are kept as tags. The `kind` column and the kinds table are
  dropped by a migration.
- Personalization learns at every level of the path, so a dislike of `Dev > PHP` also colours `Dev` a little.
- The dashboard shows the categories as a tree with counts, always at hand beside the inbox.
- After creating a category the dashboard asks whether to file existing items again, and says how many would move.

## Consequences

One idea instead of two, a navigation tree, and generalising learning. The "what it is" signal moves from a closed list
to free tags, which is looser but costs the user no vocabulary. Items already filed in a category that later gets
subcategories can be re-read to move down.

## Alternatives considered

Keeping two axes with better labels: the user already found it confusing. Folders of categories only for display
(no semantics): then a source could not feed a whole branch and filtering a branch would not work.
