# Stack Watch Specification (stack-watch)

## Purpose

Know what the user depends on, so relevance can be decided by code.

## Requirements

### Requirement: Declared stack

The configuration SHALL declare the stack as entries with a name, an ecosystem (`pypi`, `npm`, `crates`, `go`,
`github`, `other`), optional version or range and optional aliases. Matching of an item to an entry SHALL be
case-insensitive on the name and aliases, and SHALL use the structured package data of advisories when present.

#### Scenario: Alias match

- **WHEN** an entry `postgresql` has the alias `postgres` and an item mentions "Postgres 17 released"
- **THEN** the item is matched to the entry

### Requirement: Version awareness

When an advisory gives affected ranges and the stack entry gives a version, the item SHALL be marked as affecting the
stack only when the version falls in a range; without a declared version it SHALL be treated as affecting.

### Requirement: Match recorded

Matched stack entries SHALL be stored on the item and shown in the dashboard.
