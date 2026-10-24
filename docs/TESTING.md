# Testing

The rule: nothing ships that has not passed every layer, and every layer is deterministic. No test reaches the network
or a real LLM. A change that touches behaviour comes with a test that fails without it, and a bug starts with a
failing test ([ADR 0009](adr/0009-testing-strategy.md)).

| Layer     | Command          | Covers                                                                                        |
| --------- | ---------------- | --------------------------------------------------------------------------------------------- |
| Python    | `just test`      | every use case through its public entry on fakes and a real SQLite file; 100% line and branch |
| Contracts | `just contracts` | `import-linter`: the hexagonal dependency rules                                               |
| Frontend  | `just ui-test`   | every component and state in Vitest + Testing Library; 100% line and branch                   |
| Journeys  | `just e2e`       | Playwright against the real backend and built frontend, on demo data and a fake LLM           |
| Docs      | `just docs`      | the guide builds with no dead link; generated reference pages match the code                  |
| Gate      | `just quality`   | format, lint, types, all of the above. `nix run .#quality` is the same command                |

## Non-regression tests (NRT)

Tests are scenarios from the specs, run at the use-case level, not unit tests of internals:

- Build the application with fakes for the network ports (`FakeSourceFetcher`, `ScriptedEnricher`, `FixedClock`) and
  the real SQLite adapter on a temp file.
- Drive it through its public entry (use case, or the HTTP app with `httpx`), and assert what the user would see.
- Name the test after the scenario (`test_critical_advisory_on_declared_dependency_is_never_below_p1`).

Adapters that parse the outside world (RSS, GitHub JSON, OSV) are tested against **recorded fixtures** in
`tests/fixtures/`, including a malformed and a hostile one. The GitHub `gh` adapter is tested against a fake `gh`
executable.

## Coverage

`pytest --cov` with `fail_under = 100`, branch coverage on. A line that cannot be reached is deleted, not excluded;
`# pragma: no cover` needs a reason in the line and a reviewer's agreement. Frontend thresholds are 100% in
`vitest.config.ts`.

## Golden set for the model

`tests/golden/*.json`: items with the priority and category they must get. Replayed against recorded model answers
(cassettes) in CI for free. Re-recording is a deliberate, local act (`just golden-record`) against a real endpoint.

## Journeys

`e2e/` drives the real UI: open the inbox, filter by priority, mark an item seen, done, snooze it, dismiss it, star it,
add a source, see the "why this rank" panel, keyboard shortcuts, empty and error states. Failure traces and screenshots
are uploaded as CI artifacts.

## Adding a test

- **A new use case or rule**: a scenario in the spec, then a NRT named after it.
- **A new source adapter**: a fixture (real answer, trimmed), a malformed one, a failure (timeout, 403, rate limit).
- **A new screen, control or state**: a Vitest test of the component and a Playwright step in a journey.
- **A bug found anywhere**: first a failing test, then the fix.
