<!-- Title: Conventional Commits, e.g. "feat(sources): add the OSV advisory adapter". The title becomes the commit on main. -->
<!-- The path every change follows: docs/EVOLVING.md -->

## Summary

<!-- What changes and why, in a few lines. -->

## Decision and spec

<!-- ADR added or "none needed" (docs/adr/). Spec requirement added or changed (openspec/specs/...), or "no behaviour change". -->

## Verified

<!-- What was run: `nix run .#quality`, smoke, end-to-end tests. State what was NOT verified. -->

## Checklist (docs/EVOLVING.md)

- [ ] ADR when the shape of the system changes
- [ ] Spec updated first when behaviour changes
- [ ] Tests with the code, including a non-regression test for every rule or bug; the gate passes (100% coverage)
- [ ] UI change: an end-to-end test (Playwright) that fails without it
- [ ] Guide updated (`docs/guide/`); README if the overview changed; website if a user would notice; roadmap updated
- [ ] Commits and PR title follow Conventional Commits
