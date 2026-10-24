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

# Journeys in a real browser against the real backend, a fake feed and a fake model
e2e: ui-build
    npm run --prefix frontend e2e

# The gate: the same command locally and in CI
quality: fmt-check lint types contracts test api-check ui-lint ui-types ui-test e2e

dev:
    @echo "dev server arrives with the HTTP adapter"

doctor:
    uv run lookout --help
