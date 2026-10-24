# The dashboard

Start it with `lookout serve` and open `http://127.0.0.1:8899`.

## The inbox

Items are ordered by priority, then by your profile, then by date. Each row shows its priority **in words** (colour is never the only signal), channel, kind, source, author and age.

Filters are kept in the address, so a filtered inbox can be bookmarked:

- priority chips, view (Inbox, Snoozed, Done, Dismissed, Everything)
- channel (the topic) and kind (what it is), source, starred, and free text over title, summary, tags and author

**Mark P2 and P3 as seen** clears the quiet items in one click.

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

## Sources

The **Sources** page shows each source's last run, item count and last error, and lets you switch it off or on. A source disabled in `lookout.yaml` can only be enabled there.

## Run now

**Run now** fetches every source and has the model read what is new, in the background. Only one run happens at a time.
