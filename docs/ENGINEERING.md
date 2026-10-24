# How Lookout is built

## Shape

Hexagonal (ports and adapters), with a domain model in the DDD sense. Dependencies point inward.

```
                    ┌───────────────────────── adapters (inbound) ───────────────────────┐
                    │  http (FastAPI)      cli (Typer)      scheduler                    │
                    └───────────────┬────────────────────────────────────────────────────┘
                                    ▼
                    ┌────────────── application ──────────────┐
                    │ use cases: ingest, enrich, rank, triage, │
                    │ learn, doctor        ports (interfaces)  │
                    └───────────────┬──────────────────────────┘
                                    ▼
                    ┌────────────── domain ────────────────────┐
                    │ Item, Source, Priority, Category, State, │
                    │ Profile, Stack, PriorityPolicy           │
                    └──────────────────────────────────────────┘
                                    ▲
                    ┌───────────────┴───────── adapters (outbound) ──────────────────────┐
                    │ sources: rss, hn, reddit, github (gh|api), osv, nvd                │
                    │ llm: openai-compatible   store: sqlite   clock, notifier           │
                    └────────────────────────────────────────────────────────────────────┘
```

`bootstrap/` reads `lookout.yaml` and wires adapters to ports. It is the only place that knows every adapter.

## Layout

```
src/lookout/
  domain/        pure model and rules
  application/   use cases and ports (typing.Protocol)
  adapters/      sources/ llm/ store/ http/ cli/ scheduler/
  bootstrap/     configuration and wiring
frontend/        React + Vite + TypeScript
docs/guide/      the user guide (VitePress)
site/            the website (static)
tests/           non-regression tests, golden set, fakes
e2e/             Playwright journeys
nix/             flake modules (dendritic)
openspec/        specs and proposals
```

## The item pipeline

```
SourceFetcher.fetch() ─▶ normalise ─▶ dedupe (url hash, title similarity) ─▶ store (state=new)
                                                                              │
Enricher (LLM, JSON) ◀───────────────────────────────────────────────────────┘
   summary, category, tags, llm_score, action_needed, reason
                                  │
PriorityPolicy: priority = max(rule_floor, band(llm_score + profile_boost)); reason recorded
                                  │
Inbox ranking: urgency band first, then personal score (stars, reads, dismissals, embeddings)
```

## Ports

| Port             | Role                                              | Adapters today                       |
| ---------------- | ------------------------------------------------- | ------------------------------------ |
| `SourceFetcher`  | Turn a configured source into raw items           | rss, hn, reddit, github, osv, nvd    |
| `GitHubGateway`  | Releases, advisories, Dependabot alerts of a repo | `gh` CLI, REST with a token          |
| `Enricher`       | Summarise, categorise, score one item             | OpenAI-compatible chat (JSON schema) |
| `Embedder`       | Vectors for similarity and personalization        | OpenAI-compatible embeddings         |
| `ItemRepository` | Persist items, states, feedback, profile          | sqlite                               |
| `Clock`          | Time                                              | system, fixed (tests)                |
| `Notifier`       | Push P0/P1 out of the inbox                       | none yet                             |

## Data

One SQLite file (`data/lookout.db`), versioned migrations applied on startup in a transaction each, with a backup copy
before the first pending step (ADR 0004).

## Configuration

`lookout.yaml` declares sources, the stack (packages, frameworks, versions) used by the priority rules, the LLM
endpoint and the schedule. Secrets come from the environment, never from the file.

## Design

One design, "Samurai calm", on all three surfaces: warm paper and soft ink in light, a brown-black lacquer with muted gold in
dark, serif headings, one-pixel rules, a small vermilion seal for urgency, a tinted (not solid) P0. Text is about 12:1 against
its background, and every text and badge pair stays above 4.5:1.

| Surface   | Where it lives                                                                                        |
| --------- | ----------------------------------------------------------------------------------------------------- |
| Dashboard | the tokens and rules of `frontend/src/styles.css`, with the Samurai layer in `frontend/src/theme.css` |
| Guide     | `docs/guide/.vitepress/theme/custom.css` (the VitePress variables)                                    |
| Website   | the `:root` tokens and the few rules at the top of `site/index.html`                                  |

The palettes are repeated in these three places on purpose: each is a separate build with no shared stylesheet. Change one,
change the others. The dashboard's accessibility scans run in light and dark (`frontend/e2e/journeys.spec.ts`), so a palette that
fails contrast fails the gate.

## Quality

See `docs/TESTING.md`. The gate (`nix run .#quality`) is the same command locally and in CI.
