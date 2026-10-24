# Personalization Specification (personalization)

## Purpose

Learn from what the user does, and show why an item ranks where it does.

## Requirements

### Requirement: Signals

Opening, starring, marking done, snoozing and dismissing SHALL be recorded as signals with weights (star and done
positive and strong, open mildly positive, dismiss negative, snooze neutral). Signals SHALL decay with a configurable
half-life.

#### Scenario: Dismissals teach

- **WHEN** the user dismisses five items from one source in a category
- **THEN** later items of that source and category rank lower inside their priority band

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
