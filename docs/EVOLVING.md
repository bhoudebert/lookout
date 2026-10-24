# How Lookout evolves

Every feature goes through the same path, whoever builds it, a person or a coding agent. The path exists so that each
change is designed before it is coded, specified before it is tested, and explained before it is released.

```
idea ─▶ decision ─▶ spec ─▶ code + tests ─▶ docs ─▶ website ─▶ PR + CI ─▶ release
        (ADR)      (openspec)  (100% gate)    (guide)   (site)    (merge)  (automatic)
```

## 1. Idea

Ideas live in `ROADMAP.md` or an issue. Before building, say: who needs it, when it is used, what the user does and
what Lookout does. A feature that cannot be described in those terms is not ready.

## 2. Decision: an ADR when the shape of the system changes

New data store or table, new port, new dependency or service, a rule that cuts across features, a choice between real
alternatives: write a record in `docs/adr/` from `template.md`, with the alternatives that lost. Small features inside
an existing shape need no record.

## 3. Spec: what the system shall do

Update or add `openspec/specs/<capability>/spec.md`: requirements written as SHALL statements, each with at least one
scenario (WHEN / THEN). A new capability gets its own folder and a line in `openspec/README.md`. The spec is written
first and reviewed with the code in the same pull request.

## 4. Code and tests

- **One implementation, every entry point.** Logic lives in `domain/` and `application/`; the HTTP API, the CLI and the
  scheduler are thin adapters over the same use cases. A feature reachable in one is reachable in the others unless the
  spec says why not.
- **Rules in code.** Anything that must always hold is enforced in the domain, never only in a prompt.
- **Tests with the code.** Every scenario of the spec has a non-regression test that runs the use case on fakes and a
  real SQLite file. The gate requires 100% line and branch coverage. See `docs/TESTING.md`.
- **UI.** A change to what a user sees or does comes with a Playwright journey that fails without it.

## 5. Docs

The guide (`docs/guide/`): what the feature is for, how to use it, its limits; a page for a new task, and a line in the
sidebar. The reference pages (commands, settings, sources) are generated from the code and CI fails when they are
stale. README only when the overview changes; `docs/ENGINEERING.md` when the architecture, a port or an adapter
changes; `AGENTS.md` or `CONTRIBUTING.md` when the way of working changes; `ROADMAP.md`: remove what is done, add what
was learnt.

## 6. Website

A feature a user would notice earns its place on the site (`site/`): same design language, real examples, no invented
figures.

## 7. Pull request

Conventional Commits, one concern per commit, in the order of this path (`docs(adr)`, `docs(spec)`, `feat`, `test`,
`docs`). The PR title is a Conventional Commit too: it becomes the commit on `main`. CI must be green; squash merge.

## 8. Release

Nothing to do by hand. release-please turns `feat` and `fix` commits on `main` into a release pull request with the
version and the changelog; merging it tags the release, publishes the notes and the container image.
