# How Lookout thinks

## Items

An **item** is one piece of content from a source: a blog post, a release, an advisory. Lookout stores each story once. The same link arriving from two sources (after removing tracking parameters) is one item that lists both sources.

Text from the internet is **data, never instructions**. Markup is stripped, sizes are bounded, and a title that says "ignore previous instructions" is stored as plain text and decides nothing.

## Reading

For each new item the model returns a summary, a category (the most specific that fits), up to five tags, an importance score from 0 to 100, whether you must act, and one sentence of reasoning. The answer is validated; one invalid answer gets one repair attempt, then the item stays in the inbox, flagged as not read. Nothing is ever dropped.

A daily call limit protects a paid model. When it is spent, items wait, and the rules below still apply to them.

## Categories

A **category** is where an item lives: AI, Security, `Dev > Rust`. You define them on the **Categories** page, each with a one-line description the model can use. They form a tree: `Dev > Rust` sits inside `Dev`, up to four levels, and choosing `Dev` in the inbox shows both. `Other` always exists. What an item _is_ (a release, a security fix, a deprecation, an outage) is not a second axis: the model adds it as a tag. (The code and the API call a category a _channel_.)

Each source says which categories it may feed. With **one**, its items are filed there before any model sees them (a Rust blog feeds `Rust`). With several, or none, the model chooses among them, picking the most specific that fits and `Other` only as a last resort. An item never leaves its source's categories.

### New categories and the items you already have

**Run now reads new items only**: an item already stored is never fetched or read again, and there is no "from date". So categories you add later apply to new items. To move what is already in your inbox, press **File existing items again** on the Categories page: items from a source that feeds exactly one category go there at once, and items the model left in `Other`, or in a category that has since gained subcategories, are queued to be read again at the next run, within your daily model limit.

The **author** and the **tags the article itself carries** are facts from the source: the model never changes them, and its own tags are kept alongside. All of them, plus the source, feed [what Lookout learns about you](/personalization).

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
