# Stack Watch Specification (stack-watch)

## Purpose

Know what the user depends on, so relevance can be decided by code.

## Requirements

### Requirement: Declared stack

The configuration SHALL declare the stack as entries with a name, an ecosystem (`pypi`, `npm`, `crates`, `go`,
`github`, `other`), an optional version and optional aliases. Matching of an item to an entry SHALL be
case-insensitive on the name and aliases, and SHALL use the structured package data of advisories when present.

#### Scenario: Alias match

- **WHEN** an entry `postgresql` has the alias `postgres` and an item mentions "Postgres 17 released"
- **THEN** the item is matched to the entry

### Requirement: Version awareness

When a stack entry gives a version, advisory sources that can filter by version (OSV) SHALL ask only for
vulnerabilities affecting it; without a declared version every recent vulnerability of the package SHALL be treated as
affecting.

### Requirement: Match recorded

Matched stack entries SHALL be stored on the item and shown in the dashboard.
