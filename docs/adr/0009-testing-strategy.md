# 0009. Testing: non-regression scenarios, 100% coverage, journeys, cassettes

- Status: accepted
- Date: 2026-10-24

## Context

The owner wants the same test accuracy as the MotoRide app: nothing ships without passing layered, deterministic tests,
with few hand-written unit tests but full coverage reached through realistic non-regression scenarios.

## Decision

1. Python: scenario tests at use-case level on fakes and a real SQLite file; coverage gate 100% lines and branches.
2. Adapters: recorded fixtures (normal, malformed, hostile, failing) and a fake `gh` executable.
3. Frontend: Vitest + Testing Library with a 100% gate; Playwright journeys against the real built stack with demo data
   and a fake LLM.
4. Model behaviour: a golden set of items with expected priority and category, replayed from recorded answers for free
   in CI; re-recording is deliberate and local.
5. Docs: the guide builds with no dead link; generated reference pages are checked for staleness.
6. One gate command, identical locally and in CI. No test reaches the network or a real model.

## Consequences

A regression in rules, parsing, state transitions or UI flow fails CI. Prompt quality is measured only on
re-recording, which is a deliberate act. 100% coverage means untestable code is removed or isolated.

## Alternatives considered

A coverage threshold of 80%: leaves rules uncovered. Live end-to-end tests in CI: flaky and costly.
