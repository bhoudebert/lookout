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

### Requirement: Sources view

The user SHALL see each source with its last run, item count and last error, and enable or disable it. Adding sources
is done in the configuration file in v0.

### Requirement: States of the screen

Loading, empty, error and offline-backend states SHALL be shown explicitly.

### Requirement: Accessible

Controls SHALL be reachable by keyboard and labelled; colour SHALL NOT be the only carrier of priority.
