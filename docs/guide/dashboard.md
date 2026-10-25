# The dashboard

Start it with `lookout serve` and open `http://127.0.0.1:8899`.

## The inbox

By default (**Triage**) items are ordered by priority, then by your profile, then by date; **Latest** shows the newest first, whatever the priority, with a line before what arrived since your last visit. Each row shows its priority **in words** (colour is never the only signal), category, source, author, tags and age.

Filters are kept in the address, so a filtered inbox can be bookmarked:

- priority chips, order (Triage or Latest), view (Inbox, Snoozed, Done, **Expired**, Everything) and age (newer than a week, older than a week, two weeks, a month)
- category (picked in the tree beside the list, subcategories included; the numbers in the tree are what the list would show with the other filters, so they change with the view, age and the rest), source, starred, and free text over title, summary, tags and author

A search only looks where you are: in the Inbox view, done, snoozed and expired items are not searched. When you type a search outside **Everything**, a note says so and **Search everything** widens it in one click (every state, every age). Search reads the title, summary, tags and author, not the full text, and cannot find entries that were older than the source's age limit when they arrived.

The list loads 50 items at a time: **Load more** fetches the next 50, and the count always says the real total ("50 of 2329").

**Mark P2 and P3 as seen** clears the quiet items in one click. **Act on all N…** acts on everything the current filters match, not only what is loaded: it counts first, shows a few examples, asks you to choose (done, seen, thumbs up, thumbs down or clear the rating), and offers Undo. It teaches your profile nothing, and nothing is deleted. See [keeping the inbox small](/inbox-size).

## An item

Click a title, or press `o`, and the panel opens on the right. Moving with `j` and `k` shows each item in it as you go, like the preview pane of a mail client; that is only a preview, so it does not mark the items seen or teach anything. Pressing `o` or Enter, or clicking, is what counts as reading. The panel shows the summary, the original text, a link to the source, the stack entries it touches, the priority reason and **Why this rank**. Opening a new item marks it seen.

## Thumbs and Done

Every item, in the list and in its panel, has three controls:

- **Thumbs up** and **thumbs down** say whether you want more or less of this. The pressed thumb is the item's rating; pressing it again clears it. A rating teaches your profile (its source, author, category and tags) and **never removes the item**.
- **Done** clears the item from the inbox and teaches nothing. The panel moves on to the next item, which takes the focus, so you can keep going with `e`.

Use a thumb down and Done together for noise, a thumb up for what you want more of, and Done alone to tidy. See [how it learns your taste](/personalization).

## Acting

| Key        | Does                                          |
| ---------- | --------------------------------------------- |
| `j` / `k`  | next / previous item                          |
| `o`, Enter | open                                          |
| `e`        | done: clear the item from the inbox           |
| `+` / `-`  | thumbs up / thumbs down                       |
| `s`        | snooze (1 hour, 4 hours, tomorrow, next week) |
| `*`        | star / unstar                                 |
| `x`        | select for a bulk action                      |
| `u`        | undo the last action                          |
| `?`        | help                                          |

With items selected, `e` and `s` apply to all of them; the thumbs `+` and `-` apply to the focused item, or to **all** of them when some are selected (then they _set_ the rating on every one, so ones already rated that way stay so). A bulk action is all or nothing.

Every action shows a message with **Undo** for eight seconds.

## Categories

The **Categories** page is where you define what you look at. It lists each category with its description, how many items it holds in the inbox and which sources feed it, suggests starting categories (AI, `Dev > Rust`, Security, ...) you can add with one click, and lets you add, describe and delete your own, inside another category if you want. Each category can have an **icon**, one emoji shown before its name in the tree, on this page and beside its items. After a run, the model suggests one for every category that has none (once; nothing is asked again for a category you cleared); **Suggest icons** asks for the categories still without one. Click **Edit** to type your own or to clear it; an icon is one emoji, never text. You can **move** a category (with what is under it) inside another or back to the top level; its items and sources follow. After you create one, the page tells you how many items it could file again and asks before touching them; **File existing items again** does it at any time. While everything in your inbox is still in `Other`, the inbox tells you so and links here. See [how Lookout thinks](/concepts).

## Sources

The **Sources** page shows each source's type, categories, last run, item count and last error. From there you add, edit, switch and delete sources. See [sources](/sources).

## Run now

**Run now** fetches every source and has the model read what is new, in the background. Only one run happens at a time.
