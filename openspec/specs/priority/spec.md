# Priority Specification (priority)

## Purpose

Give every item a priority that can be trusted and explained.

## Requirements

### Requirement: Levels

Priority SHALL be one of P0 (act today), P1 (this week), P2 (read when free), P3 (background).

### Requirement: Rule floors

Deterministic rules SHALL set a minimum priority: an advisory or alert of critical severity affecting a declared
package SHALL be at least P0; high severity at least P1; any advisory in the CISA KEV catalogue affecting a declared
package at least P0; a release of a declared package that changes its major version at least P1; a Dependabot alert on
a watched repository at least P1.

#### Scenario: Critical advisory on a declared package

- **WHEN** an advisory with severity critical affects `django` and `django` is in the declared stack
- **THEN** the item is P0 whatever score the model gave it, and its reason names the rule

### Requirement: Model score and profile

Above the floor, the priority SHALL come from the model score plus the profile boost, banded by configurable
thresholds. The model SHALL NOT lower a priority below its floor.

#### Scenario: Model underrates

- **WHEN** the model scores a floor-P1 item at 5
- **THEN** the item is P1

### Requirement: Recorded reason

Every item SHALL store how its priority was reached (floor rule, score, boost) and the dashboard SHALL show it.

### Requirement: Recompute

Changing the stack or the thresholds SHALL allow recomputing priorities of stored items without calling the model.
