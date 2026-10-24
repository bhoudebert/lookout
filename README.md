# Lookout

A self-hosted watch tower for the feeds, releases and advisories that matter to your work.

Plug in sources, let an LLM summarise, categorise and prioritise each item, and work an inbox: seen, done, snoozed,
dismissed. Lookout learns from what you act on.

- **Sources as adapters:** RSS/Atom, Hacker News, Reddit, GitHub releases, GitHub security advisories and Dependabot
  alerts (through your local `gh` login), OSV and NVD. More are one adapter away.
- **Any LLM:** one OpenAI-compatible port. Starts on Ollama (free, local); point it at any compatible endpoint later.
- **Priority you can trust:** P0 to P3, from deterministic rules first (a critical advisory on a dependency you
  declared is never below P1), the model second. Every priority carries its reason.
- **Personal:** stars, reads and dismissals shape the ranking; the "why this rank" is always visible.
- **Triage, not a digest:** an inbox with states, keyboard shortcuts and filters by priority, category and source.
- **Yours:** one SQLite file, one container, MIT licence.

## Quick start

```
nix develop            # Python, uv, Node, just, gh
just setup
just dev               # demo data, backend on :8899, UI on :5173
```

Real use: copy `lookout.example.yaml` to `lookout.yaml`, declare your sources and your stack, start Ollama, then
`lookout serve`.

## Documentation

- The guide: `docs/guide/` (built with `just docs`), and the website in `site/`.
- How it is built: `docs/ENGINEERING.md`. How it is proven: `docs/TESTING.md`. Why: `docs/adr/`.
- What it shall do: `openspec/specs/`.
- How changes happen: `AGENTS.md`, `docs/EVOLVING.md`.

## Status

Early. See `ROADMAP.md`.
