# 0010. Conventional Commits, squash merges, release-please

- Status: accepted
- Date: 2026-10-24

## Context

Versions and changelogs should come from history, not from memory.

## Decision

Conventional Commits enforced by a commit-msg hook and in CI (commitlint, PR title check). Squash merge only, so the PR
title is the commit on `main`. release-please maintains a release PR with version and changelog; merging it tags the
release and publishes the container image. `main` is protected: a pull request and green CI are required, for
everyone.

## Consequences

Predictable history and releases. Contributors must write good PR titles.

## Alternatives considered

Manual tags: forgotten. Semantic-release: needs more CI privileges.
