# Lookout

A self-hosted watch tower for the feeds, releases and advisories that matter to your work.

Plug in sources, let an LLM summarise, categorise and prioritise each item, and work an inbox: seen, done, snoozed,
dismissed. Lookout learns from what you act on.

- **Sources as adapters:** RSS and Atom today (which covers blogs, GitHub releases, Reddit, Hacker News and YouTube
  channels); GitHub advisories and Dependabot alerts (through your local `gh` login), OSV and NVD are next. Each is one
  adapter away.
- **Any LLM:** one OpenAI-compatible port. Starts on Ollama (free, local); point it at any compatible endpoint later.
- **Priority you can trust:** P0 to P3, from deterministic rules first (a critical advisory on a dependency you
  declared is never below P1), the model second. Every priority carries its reason.
- **Personal:** stars, reads and dismissals shape the ranking; the "why this rank" is always visible.
- **Triage, not a digest:** an inbox with states, keyboard shortcuts and filters by priority, category and source.
- **Yours:** one SQLite file, one container, MIT licence.

## Quick start

```
nix develop            # Python, uv, Node, just, gh, Chromium for the tests
just setup
cp lookout.example.yaml lookout.yaml
lookout demo           # six believable items, no model needed
npm run --prefix frontend build
lookout serve          # http://127.0.0.1:8899
```

For real use, edit `lookout.yaml` (your sources, your stack, a sentence about your interests), start Ollama, check with
`lookout doctor`, then `lookout run` or press **Run now**.

Sources today: any RSS or Atom feed, which already covers blogs, GitHub releases (`/releases.atom`), Reddit (`.rss`),
Hacker News (`hnrss.org`) and YouTube channels. Advisory and Dependabot adapters are next, see `ROADMAP.md`.

## Documentation

- The guide: `docs/guide/` (built with `just docs`), published with the website in `site/` on GitHub Pages.
- How it is built: `docs/ENGINEERING.md`. How it is proven: `docs/TESTING.md`. Why: `docs/adr/`.
- What it shall do: `openspec/specs/`.
- How changes happen: `AGENTS.md`, `docs/EVOLVING.md`.

## Status

Early (v0.x): the core, the CLI, the HTTP API and the dashboard work; see `ROADMAP.md` for what is next.
