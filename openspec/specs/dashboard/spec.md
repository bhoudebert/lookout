# Dashboard Specification (dashboard)

## Purpose

The web inbox where the user works.

## Requirements

### Requirement: Inbox view

The dashboard SHALL list the inbox with priority badge, title, source, channel, author, tags, summary and age, grouped or ordered by
priority band, and filterable by priority, channel, source, state, star and text. Filters SHALL be reflected in the URL.

The list SHALL offer two orders, Triage (priority, the default) and Latest (newest first, with a divider before what
arrived since the user's last visit), kept in the URL. It SHALL load 50 items at a time with a "Load more" control and
the real total, in both orders and in every view, including `expired`.

While a text search is typed and the view is not `all`, the dashboard SHALL say which view is being searched and offer
one control that switches to the `all` view and clears the age filter.

#### Scenario: Filter by priority

- **WHEN** the user selects P0 and P1
- **THEN** only those items are listed and the URL carries the filter

### Requirement: Item detail

Selecting an item SHALL show summary, original excerpt, link to the source, matched stack entries, the priority reason
and the "why this rank" breakdown.

### Requirement: Actions and keyboard

The user SHALL be able to mark seen, done, snooze (preset durations or a date) and star, rate an item up or down, per item and in bulk (rating per item),
with keyboard shortcuts (`j`/`k` move, `o` open, `e` done, `+` thumbs up, `-` thumbs down, `s` snooze, `*` star, `u` undo, `?` help). The
last action SHALL be undoable.

### Requirement: The panel follows the keys

Moving with `j` and `k` SHALL show the item reached in the panel on the right, opening the panel if it was closed. That
is a preview: it SHALL NOT mark the item seen or count as having read it (only `o`, Enter or a click does), and it SHALL
replace the page in the browser history instead of adding an entry for every item passed.

#### Scenario: Skimming

- **WHEN** the user presses `j` three times on new items
- **THEN** the panel shows the third item, none of them is marked seen, and the profile has learnt nothing

### Requirement: Rating and clearing

Each item in the list and in the detail SHALL show a thumbs up, a thumbs down and a Done button; a pressed thumb shows the
item's rating and pressing it again clears it. Done SHALL remove the item from the list and move to the next item;
if the removed item was shown in the panel, the panel SHALL show the next one, or close when none is left. A rating SHALL leave the item where it is. The thumb shortcuts SHALL apply to the
whole selection when items are selected (setting, not toggling), the bar of the selection SHALL have both thumbs, and the
dialog that acts on a whole filter SHALL offer both thumbs and clearing a rating next to done and seen.

### Requirement: The shell

The dashboard SHALL be one light frame on every screen: a sidebar holding the product name, the four screens
(Inbox, Digest, Sources, Categories) with a count on the inbox and on the sources, the category tree on the inbox, and
when the last run finished; a top bar holding a search over items, sources and tags (focused by the `/` key), the state
of the digest and Run now; and the screen itself on a sheet beside them. Category icons SHALL NOT appear in the
dashboard outside the categories page. Every screen SHALL have one `h1` naming it. Below 900px the sidebar SHALL stack
above the sheet, with the categories in one scrolling row, so nothing is unreachable on a phone.

#### Scenario: A phone

- **WHEN** the window is 390px wide
- **THEN** the product name, the screens and the categories are reachable above the sheet, and the page does not scroll sideways

### Requirement: Views as tabs

The views of the inbox (Inbox, Snoozed, Done, Expired, Everything) SHALL be tabs above the list, the chosen view marked
as selected and kept in the URL, the Inbox tab carrying the number of items it holds. Under them the list SHALL have
one field to filter it, the priority buttons, and the other filters (source, age, starred) behind "More filters"; under
those, how many items are shown, the order (Triage or Latest) and a menu of actions on the whole list.

#### Scenario: Looking at what was done

- **WHEN** the user chooses the Done tab
- **THEN** the done items are listed and the tab is selected

### Requirement: Three regions

On a wide screen the inbox SHALL show the list, the open item and its details side by side, each scrolling on its own.
A row SHALL show the mark of its source, the title, the source and the category, its age and, above normal, its
priority; P2 and P3 SHALL be written for assistive technology and in the panel. The thumbs and Done of a row SHALL appear
when the row is pointed at or focused. The panel SHALL always show an item: the one opened, else the one the list is on,
as a preview that reads nothing. Under the title the dashboard SHALL name what needs action today when something does.

#### Scenario: Nothing opened

- **WHEN** the inbox opens with items in it
- **THEN** the panel shows the first item, none is marked seen, and the URL names no item

### Requirement: The last run at a glance

Above the list the inbox SHALL show the last run as one bar of everything it fetched, split into what was new and what
was already known, with both counts and the time it finished, and say how many items wait for the model. While a run is going it SHALL say so, and
when the last run failed it SHALL say that, not draw a bar. Before any run it SHALL show nothing.

#### Scenario: A run with news

- **WHEN** the last run fetched 148 items of which 31 were new
- **THEN** the strip shows "148 fetched", "31 new" and "117 already known", and the new part of the bar is 31/148 of its width

### Requirement: Sources view

The user SHALL see each source with its last run, item count and last error, and enable or disable it. Adding sources
is done in the configuration file in v0.

### Requirement: States of the screen

Loading, empty, error and offline-backend states SHALL be shown explicitly.

### Requirement: Accessible

Controls SHALL be reachable by keyboard and labelled; colour SHALL NOT be the only carrier of priority.
