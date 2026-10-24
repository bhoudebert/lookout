# GitHub Sources Specification (github-sources)

## Purpose

Follow releases, security advisories and Dependabot alerts of declared repositories.

## Requirements

### Requirement: Declared repositories

Repositories SHALL be declared as `owner/name` with the kinds wanted (`releases`, `advisories`, `dependabot`).

### Requirement: Access through gh or a token

The adapter SHALL use the local `gh` executable when present and logged in, otherwise the REST API with a token from
the environment. `doctor` SHALL report which is used and whether it can read each declared repository.

#### Scenario: No gh, no token

- **WHEN** neither is available
- **THEN** `doctor` reports it and the GitHub sources fail with that message, other sources are unaffected

### Requirement: Items

A release SHALL become an item with the tag, notes and URL. An advisory or Dependabot alert SHALL become an item with
severity, affected package, ecosystem, affected and patched ranges, CVE/GHSA ids and URL, in structured fields used by
the priority rules.

### Requirement: Rate limits

The adapter SHALL respect rate-limit headers and use conditional requests where available.
