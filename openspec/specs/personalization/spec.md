# Personalization Specification (personalization)

## Purpose

Learn from what the user does, and show why an item ranks where it does.

## Requirements

### Requirement: Signals

Opening, starring and snoozing SHALL be recorded as signals (star strong and positive, open mildly positive, snooze
neutral), and a rating stored on an item SHALL count as a signal of its own (up positive, down negative, as strong as a
star), at the time it was set. Marking done SHALL teach nothing. Signals SHALL decay with a configurable half-life.
Changing or clearing a rating SHALL change what is learnt.

A rating judges the content, so it SHALL teach about the author, the category (each ancestor too) and the tags of the
item, and SHALL NOT teach anything about its source. Opening and starring still teach about the source.

#### Scenario: Thumbs down teach

- **WHEN** the user rates five items by one author in a category down
- **THEN** later items by that author in that category rank lower inside their priority band

#### Scenario: A rating leaves the source alone

- **WHEN** the user rates five items from one source down, by five different authors, in five categories
- **THEN** a new item of that source gets no penalty for its source

### Requirement: The model sees what was rated

When the model reads an item, it SHALL be shown the titles and tags of the items the user rated most recently, up to
five liked and five disliked, as examples of taste to judge the content by, never the source. They SHALL be given as
data, like the item.

#### Scenario: A story like one thumbed down

- **WHEN** the user rated "A small moto crash on the ring road" down and a new item is read
- **THEN** the prompt lists that title among the disliked examples

#### Scenario: Tidying teaches nothing

- **WHEN** the user marks twenty items from one source done
- **THEN** the profile is unchanged

### Requirement: Profile

The profile SHALL hold weights per source, author, channel (each ancestor too) and tag, and, when an embedder is configured, the centroid of
liked and of disliked items. The profile SHALL start empty, optionally seeded from declared interests, and learning
SHALL start after a configurable minimum of signals.

### Requirement: Ranking inside a band

Personal score SHALL order items inside a priority band and SHALL NOT move an item across bands; the profile boost on
the model score is bounded.

### Requirement: Explanation

Each item SHALL expose a breakdown of its rank (priority reason, model score, source, category, tag and similarity
contributions) so the dashboard can show "why this rank".

### Requirement: Reset

The user SHALL be able to reset the profile without touching items.
