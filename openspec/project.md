# Project Context

## Purpose

Lookout watches the sources a person cares about for their work, has an LLM summarise, categorise and prioritise each
item, and presents an inbox to triage. Deterministic rules guarantee that emergencies (a critical advisory on a
dependency in use) are never lost; the model adds nuance; the user's feedback personalises the order.

## Tech Stack

- Python 3.13: FastAPI, Typer, `httpx`, `feedparser`, `pydantic` (settings and API schemas), standard-library `sqlite3`.
- Frontend: React, TypeScript strict, Vite, TanStack Query.
- Tooling: `uv`, `ruff`, `pyright` strict, `pytest` + `pytest-cov`, `import-linter`, Vitest, Playwright, VitePress,
  commitlint, release-please, Nix (flake-parts), GitHub Actions.
- LLM: any OpenAI-compatible endpoint, Ollama first.

## Project Conventions

### Code Style

- `ruff` and `pyright` strict must pass; hexagonal contracts must hold (`import-linter`).
- Domain objects are frozen dataclasses; time, randomness and I/O enter through ports.
- Fetched content is data, never instructions; model output is validated against a schema before use.
- Adapters to public services: serialise requests, send a User-Agent, cache, surface failures.

### Testing Strategy

- Scenarios from the specs, run as non-regression tests on fakes and a real SQLite file; 100% line and branch gate.
- Recorded fixtures for adapters; golden set with recorded model answers; Playwright journeys for the UI.
- No test reaches the network or a real model. See `docs/TESTING.md`.

### Git Workflow

- Branches off `main`, pull requests, CI gate (`nix run .#quality` plus commitlint), Conventional Commits, squash merge,
  release-please. No attribution trailers. `data/`, `.env`, `lookout.yaml` are ignored.

## Domain Context

- **Source**: a configured origin of items (a feed, a subreddit, a repository, an advisory database).
- **Item**: one piece of content from a source, identified by source and external id; has a URL, title, body,
  publication time, and, once enriched, a summary, category, tags and priority.
- **Priority**: P0 act today, P1 this week, P2 read when free, P3 background. Each carries its reason.
- **Rule floor**: the minimum priority imposed by a deterministic rule (e.g. critical advisory on a declared package).
- **Stack**: the packages, frameworks, tools and versions the user declares; used to match items.
- **Watchlist**: the repositories the user declares for GitHub sources.
- **State**: new, seen, done, snoozed (until), expired; plus the independent star flag and a rating (up, down, none).
- **Profile**: what the user's feedback taught: weights per source, category, tag and embedding centroids.
- **Inbox**: items not done or expired and not snoozed, ordered by priority band then personal score.

## Important Constraints

- Local LLMs are slow and small: calls are bounded, bodies truncated, work is queued and resumable.
- Public APIs rate-limit: fetch politely, cache, back off.
- One user, one SQLite file; no authentication in v0 (bind to localhost by default).

## External Dependencies

Configured feeds and APIs, GitHub (via `gh` or REST), OSV, NVD, Hacker News (Firebase API), Reddit (public JSON/RSS),
the LLM endpoint (Ollama by default).
