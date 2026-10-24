# GitHub Sources Specification (github-sources)

## Purpose

Follow releases, security advisories and Dependabot alerts of declared repositories.

## Requirements

### Requirement: Repositories as people write them

A repository MAY be written as `owner/name`, as its web address (with or without a trailing slash, `.git`, or a path
after the name) or as its SSH address. It SHALL be reduced to `owner/name`, the same repository listed twice SHALL be read
once, and anything that is not a GitHub repository SHALL be refused with the usual message.

### Requirement: Declared repositories

Repositories SHALL be declared as `owner/name` under a source of kind `github`, with the kinds wanted (`releases`, `advisories`, `dependabot`; default `releases` and `advisories`, since Dependabot alerts need access to the repository). A malformed repository name SHALL fail loading with a message naming the source.

### Requirement: Access through gh or a token

The adapter SHALL use the local `gh` executable when present and logged in, otherwise the REST API with a token from
the environment. `doctor` SHALL report which is used and whether it can read each declared repository.

#### Scenario: No gh, no token

- **WHEN** neither is available
- **THEN** `doctor` reports it and the GitHub sources fail with that message, other sources are unaffected

### Requirement: Items

A release SHALL become an item with the tag, notes and URL. An advisory or Dependabot alert SHALL become an item with
severity, affected package, ecosystem, CVE/GHSA ids and URL, in structured fields used by the priority rules, and with
the affected and patched ranges in its text. Draft releases SHALL be skipped; pre-releases SHALL be marked as such.

#### Scenario: Unreadable repository

- **WHEN** the token or login cannot read a repository's Dependabot alerts
- **THEN** the source fails with a message naming the repository and the kind, and other sources are unaffected

### Requirement: Rate limits

The adapter SHALL respect rate-limit headers and use conditional requests where available.
