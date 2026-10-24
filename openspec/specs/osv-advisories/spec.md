# OSV Advisories Specification (osv-advisories)

## Purpose

Bring vulnerabilities for the packages the user declared, from any ecosystem OSV covers, with severity and exploitation
status as structured facts for the priority rules.

## Requirements

### Requirement: Queried from the declared stack

A source of kind `osv` SHALL query OSV for every stack entry whose ecosystem OSV knows (`pypi`, `npm`, `crates`, `go`),
passing the entry's version when it has one so that OSV returns only vulnerabilities affecting that version. Entries of
other ecosystems SHALL be skipped. A stack with no such entry SHALL fail the source with a message saying which
ecosystems are supported.

#### Scenario: Version declared

- **WHEN** the stack declares `django` version `5.1.0`
- **THEN** OSV is asked about that version, and only vulnerabilities affecting 5.1.0 become items

### Requirement: Recent only

Only vulnerabilities published within the last `since_days` days (default 30) SHALL become items, so a first run does
not flood the inbox with history. Results SHALL be read across pages.

### Requirement: Severity as a fact

An item's severity SHALL be taken from the database's own severity when OSV gives one, otherwise computed from the
CVSS v3 base score of its vector (low under 4, moderate under 7, high under 9, critical from 9), otherwise treated as
moderate. The severity SHALL NOT come from the model.

#### Scenario: Only a CVSS vector

- **WHEN** a vulnerability has the vector `CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H` and no database severity
- **THEN** its severity is critical (base score 9.8)

### Requirement: Known exploited

When `kev` is on (the default), the CISA Known Exploited Vulnerabilities catalogue SHALL be read, and a vulnerability
with a CVE alias in it SHALL be marked as known to be exploited, which raises its floor to P0 for a declared package. A
catalogue that cannot be read SHALL fail the source with a message naming it.

#### Scenario: Exploited in the wild

- **WHEN** a moderate vulnerability on a declared package has a CVE listed by CISA
- **THEN** the item is P0 and its reason says it is known to be exploited

### Requirement: Identity

Each vulnerability SHALL be one item at `https://osv.dev/vulnerability/<id>`, titled with its id, summary and package,
with the affected and fixed versions in its text and its CVE and GHSA aliases among its identifiers.
