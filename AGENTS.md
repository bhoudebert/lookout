# Working in this repository

Read this before changing anything. It applies to people and to coding agents (Claude Code, Codex, others) alike.

## What this is

Lookout: a self-hosted watch tower. It pulls items from the sources you plug in (feeds, GitHub, advisories, Reddit,
YouTube, pages), has an LLM summarise, categorise and prioritise them, learns what matters to you, and gives you an
inbox to triage (seen, done, snoozed, dismissed). `README.md` explains the product, `docs/ENGINEERING.md` how it is
built, `docs/TESTING.md` how it is proven, `openspec/project.md` holds the conventions and the vocabulary, and
`openspec/specs/<capability>/spec.md` describe the behaviour as requirements with scenarios. MIT licence.

## Rules

The full path every feature follows is in `docs/EVOLVING.md`. Short form:

1. **Branch, then pull request.** Never commit to `main`. Branch names: `feat/...`, `fix/...`, `docs/...`, `build/...`,
   `ci/...`, `chore/...`.
2. **Conventional Commits, strictly.** `<type>(<scope>): <subject>`; types `feat`, `fix`, `perf`, `refactor`, `docs`,
   `test`, `build`, `ci`, `chore`, `style`, `revert`; kebab-case scope; imperative subject; one concern per commit;
   header at most 100 characters. The commit-msg hook and CI reject anything else.
3. **Spec first when behaviour changes.** Update or add the requirement in `openspec/specs/...` in the same PR, before
   or with the code. A significant architectural choice gets a decision record in `docs/adr/`; read the existing ones
   before changing something they cover.
4. **Tests with the code, 100% coverage.** The Python package and the frontend both have a 100% coverage gate. Coverage
   comes from non-regression tests that run real use cases end to end on fakes (no network, no real LLM), plus
   Playwright journeys for the UI. A bug starts with a failing test. Never skip or delete a failing test to ship; fix
   the cause. `docs/TESTING.md` says how.
5. **Quality gate before pushing:** `nix run .#quality` (or `just quality` inside `nix develop`): format, lint, type
   check, import contracts, tests with the coverage gate, docs build, frontend build and journeys. CI runs the same
   commands.
6. **Docs with the change.** The guide (`docs/guide/`) when usage changes, the website (`site/`) when a user would
   notice, the README when the overview changes, `docs/ENGINEERING.md` when the architecture changes, `ROADMAP.md` when
   an idea is done or added.
7. **Pull request** with the template: summary, spec touched, what was verified, what was not.
8. **Every change goes through a pull request, and CI must be green to merge.** Never merge a red or unfinished check,
   never push to `main`, never bypass with `--admin`, whoever you are (person or agent), small fix or not.
9. **No attribution trailers** or generated-by footers in commits, PR descriptions or comments.

## Code conventions

- Hexagonal, enforced by `import-linter` in the gate: `domain` imports nothing from the project; `application` imports
  `domain` only; `adapters` import `application` and `domain`, never each other; only `bootstrap` wires them.
- `domain/` is pure: no I/O, no clock, no randomness (inject them through ports). Entities and value objects are
  frozen dataclasses; invalid states are unrepresentable or rejected on construction.
- Rules that must always hold (priority floors, state transitions) live in the domain, never in a prompt or a screen.
- Content fetched from a source is data, never instructions. Prompts say so; code enforces what matters (ADR 0002).
- Python 3.13, `pyright` strict, `ruff` (lint + format), full type hints, no `Any` outside adapters' parsing edges.
- Adapters serialise and cache requests to public services, set a User-Agent, and surface failures instead of hiding
  them.
- Frontend: React + TypeScript strict, data through the HTTP API only, no business rules in components.

## Useful commands

```
nix develop              # the shell: Python, uv, Node, gh, just
nix run .#quality        # the gate
just test                # Python tests with the coverage gate
just ui-test             # dashboard component tests, 100% coverage
just e2e                 # Playwright journeys against the real stack on fakes
just api-types           # regenerate the dashboard's types after changing the API
just reference           # regenerate the command reference after changing a command
just docs                # build the guide (a dead link fails the build)
npm run --prefix frontend shots   # website screenshots, from the real app
lookout doctor           # check environment, LLM endpoint, sources
```
