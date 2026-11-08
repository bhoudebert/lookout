# Lookout

[![CI](https://img.shields.io/github/actions/workflow/status/bhoudebert/lookout/ci.yml?branch=main&label=CI)](https://github.com/bhoudebert/lookout/actions/workflows/ci.yml)
[![Release](https://img.shields.io/github/v/release/bhoudebert/lookout)](https://github.com/bhoudebert/lookout/releases)
[![Python 3.13+](https://img.shields.io/badge/python-3.13%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![Node.js 24](https://img.shields.io/badge/node-24-339933?logo=nodedotjs&logoColor=white)](https://nodejs.org/)
[![Conventional Commits 1.0.0](https://img.shields.io/badge/Conventional%20Commits-1.0.0-FE5196?logo=conventionalcommits&logoColor=white)](https://www.conventionalcommits.org/en/v1.0.0/)
[![MIT licence](https://img.shields.io/badge/licence-MIT-blue)](LICENSE)

A self-hosted watch tower for the feeds, releases and advisories that matter to your work.

Plug in sources, let an LLM summarise, classify and prioritise each item, and work an inbox: seen, done, snoozed. A thumb
up or down says what you want more or less of, and Lookout learns from it.

- **Sources as adapters:** RSS and Atom (blogs, GitHub releases, Reddit, YouTube channels), Hacker News with its points, Reddit communities, YouTube channels,
  GitHub releases, advisories and Dependabot alerts (through your local `gh` login), and OSV vulnerabilities for your
  stack. The sources page suggests good ones to start with. Each source type is one adapter.
- **Any LLM:** one OpenAI-compatible port. Starts on Ollama (free, local); point it at any compatible endpoint later.
- **Priority you can trust:** P0 to P3, from deterministic rules first (a critical advisory on a dependency you
  declared is never below P1), the model second. Every priority carries its reason.
- **Personal:** stars, thumbs and reads shape the ranking; the "why this rank" is always visible.
- **Configured in the dashboard:** define categories as a tree (AI, `Dev > Rust`, ...), and add sources (the rivers) from the dashboard; the file only seeds them.
- **Triage, not a digest:** an inbox with states, keyboard shortcuts and filters by priority, category and source.
- **Yours:** one SQLite file, one container (or a NixOS module), MIT licence.

## Quick start

```
nix develop            # Python, uv, Node, just, gh, Chromium for the tests
                       # (or `direnv allow` once: the shell then loads when you cd here)
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
