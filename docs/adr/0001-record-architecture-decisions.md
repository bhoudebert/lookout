# 0001. Record architecture decisions

- Status: accepted
- Date: 2026-10-24

## Context

Choices made early (storage, ports, test strategy) are forgotten or re-litigated unless the reasoning is kept.

## Decision

A short record per significant decision in `docs/adr/NNNN-title.md`, from `template.md`, with the alternatives that
lost. Records are not edited after acceptance except for status; a change of mind is a new record that supersedes.

## Consequences

Newcomers and coding agents can read why the system has its shape. Writing a record costs minutes per decision.

## Alternatives considered

Wiki pages: drift from the code. Commit messages only: not discoverable.
