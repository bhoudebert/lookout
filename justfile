# The gate and the everyday commands. `nix run .#quality` runs `just quality` in the dev shell.
set shell := ["bash", "-euo", "pipefail", "-c"]

default:
    @just --list

# First time: Python and Node dependencies, git hooks
setup:
    uv sync
    npm ci
    npm ci --prefix frontend
    npx simple-git-hooks

fmt:
    ruff format .
    ruff check --fix .
    npx prettier --write .

fmt-check:
    ruff format --check .
    npx prettier --check .

lint:
    ruff check .

types:
    pyright --pythonpath .venv/bin/python

# Hexagonal dependency rules (ADR 0003)
contracts:
    uv run lint-imports

# Non-regression tests with the 100% coverage gate (ADR 0009)
test:
    uv run pytest --cov --cov-report=term-missing

# Commit messages of the branch follow Conventional Commits
commits base="origin/main":
    npx commitlint --from {{base}} --to HEAD --verbose

# Frontend: lint, types, component tests at 100%, production build
ui-lint:
    npm run --prefix frontend lint

ui-types:
    npm run --prefix frontend typecheck

ui-test:
    npm run --prefix frontend test

ui-build:
    npm run --prefix frontend build

# TypeScript types follow the backend's OpenAPI document (ADR 0007)
api-types:
    uv run python scripts/dump_openapi.py > frontend/openapi.json
    npm run --prefix frontend api:types

api-check:
    uv run python scripts/dump_openapi.py | diff -q - frontend/openapi.json
    npm run --prefix frontend api:check

# The guide's command reference is generated from the command line (a test fails when it is stale)
reference:
    uv run python scripts/reference.py > docs/guide/reference/commands.md

# The user guide and the website
docs:
    npx vitepress build docs/guide

docs-dev:
    npx vitepress dev docs/guide

# Journeys in a real browser against the real backend, a fake feed and a fake model
e2e: ui-build
    npm run --prefix frontend e2e

# The gate: the same command locally and in CI
quality: fmt-check lint types contracts test api-check docs ui-lint ui-types ui-test e2e

# Run any command of the CLI: `just lookout inbox -p P0`
lookout *args:
    uv run lookout {{args}}

# The dashboard with demo data, from a clean checkout (creates lookout.yaml from the example if missing)
dev: setup ui-build
    [ -f lookout.yaml ] || cp lookout.example.yaml lookout.yaml
    uv run lookout demo
    uv run lookout serve

# Serve the dashboard and run on the schedule (build it first with `just ui-build`)
serve:
    uv run lookout serve

demo:
    uv run lookout demo

doctor:
    uv run lookout doctor
