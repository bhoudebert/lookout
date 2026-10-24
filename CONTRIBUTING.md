# Contributing

Thanks for helping. Read `AGENTS.md` (the rules) and `docs/EVOLVING.md` (the path of a change) first.

## Which contributions help most

- **A new source adapter** (a port implementation under `src/lookout/adapters/sources/`), with a recorded fixture and
  the spec scenario it satisfies.
- **An eval case**: an item the model prioritised or categorised wrongly, added to the golden set (`tests/golden/`).
- **A priority rule**: a deterministic rule (e.g. "advisory touching a declared dependency is at least P1") with its
  scenario in `openspec/specs/priority/spec.md`.

## Setup

```
nix develop        # or install Python 3.13, uv, Node 24, just by hand
just setup         # uv sync, npm ci, git hooks
just quality
```

## Commits

Conventional Commits, enforced by the commit-msg hook and in CI:

```
<type>(<scope>): <subject>

<body: what and why, wrapped at 120 columns, optional>

<footer: BREAKING CHANGE: ..., Refs #12, optional>
```

| Type       | Use for                                        | Release effect                 |
| ---------- | ---------------------------------------------- | ------------------------------ |
| `feat`     | A capability users did not have before         | minor version                  |
| `fix`      | Wrong behaviour corrected                      | patch version                  |
| `perf`     | Same behaviour, faster or cheaper              | patch version                  |
| `refactor` | Code change with no behaviour change           | none                           |
| `docs`     | Guide, website, README, specs, roadmap         | none (listed in the changelog) |
| `test`     | Tests only                                     | none                           |
| `build`    | Dependencies, tooling, Nix, scripts            | none (listed in the changelog) |
| `ci`       | GitHub Actions, Dependabot, release automation | none                           |
| `chore`    | Housekeeping that fits nowhere else            | none                           |
| `style`    | Formatting, no logic change                    | none                           |
| `revert`   | Reverts a previous commit; subject names it    | depends on what is reverted    |

A breaking change adds `!` after the scope, `feat(api)!: ...`, and a `BREAKING CHANGE:` footer explaining the
migration.

Scopes are lower-case, kebab-case, the area touched: `domain`, `sources`, `github`, `llm`, `priority`, `triage`,
`store`, `api`, `cli`, `ui`, `docs`, `site`, `nix`, `deps`, `release`. A scope is optional for changes that span the
project.

## Pull requests

One concern per PR, the template filled in, the PR title a Conventional Commit (it becomes the commit on `main`).
Squash merge only. CI must be green.
