# The dashboard

Start it with `lookout serve` and open `http://127.0.0.1:8899`.

## The inbox

By default (**Triage**) items are ordered by priority, then by your profile, then by date; **Latest** shows the newest first, whatever the priority, with a line before what arrived since your last visit. Each row shows its priority **in words** (colour is never the only signal), category, source, author, tags and age.

Filters are kept in the address, so a filtered inbox can be bookmarked:

- priority chips, order (Triage or Latest), view (Inbox, Snoozed, Done, Dismissed, **Expired**, Everything) and age (newer than a week, older than a week, two weeks, a month)
- category (picked in the tree beside the list, subcategories included), source, starred, and free text over title, summary, tags and author

The list loads 50 items at a time: **Load more** fetches the next 50, and the count always says the real total ("50 of 2329").

**Mark P2 and P3 as seen** clears the quiet items in one click. **Act on all N…** acts on everything the current filters match, not only what is loaded: it counts first, shows a few examples, asks you to choose (done, dismissed or seen), and offers Undo. It teaches your profile nothing, and nothing is deleted. See [keeping the inbox small](/inbox-size).

## An item

Click a title, or press `o`. The panel shows the summary, the original text, a link to the source, the stack entries it touches, the priority reason and **Why this rank**. Opening a new item marks it seen.

## Acting

| Key        | Does                                          |
| ---------- | --------------------------------------------- |
| `j` / `k`  | next / previous item                          |
| `o`, Enter | open                                          |
| `e`        | done                                          |
| `d`        | dismiss                                       |
| `s`        | snooze (1 hour, 4 hours, tomorrow, next week) |
| `*`        | star / unstar                                 |
| `x`        | select for a bulk action                      |
| `u`        | undo the last action                          |
| `?`        | help                                          |

With items selected, `e`, `d` and `s` apply to all of them. A bulk action is all or nothing.

Every action shows a message with **Undo** for eight seconds.

## Categories

The **Categories** page is where you define what you look at. It lists each category with its description, how many items it holds and which sources feed it, suggests starting categories (AI, `Dev > Rust`, Security, ...) you can add with one click, and lets you add, describe and delete your own, inside another category if you want. You can **move** a category (with what is under it) inside another or back to the top level; its items and sources follow. After you create one, the page tells you how many items it could file again and asks before touching them; **File existing items again** does it at any time. While everything in your inbox is still in `Other`, the inbox tells you so and links here. See [how Lookout thinks](/concepts).

## Sources

The **Sources** page shows each source's type, categories, last run, item count and last error. From there you add, edit, switch and delete sources. See [sources](/sources).

## Run now

**Run now** fetches every source and has the model read what is new, in the background. Only one run happens at a time.
