# The gate and the everyday commands. `nix run .#quality` runs `just quality` in the dev shell.
set shell := ["bash", "-euo", "pipefail", "-c"]

default:
    @just --list

# First time: Python and Node dependencies, git hooks
setup:
    uv sync
    npm ci

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

# The gate: the same command locally and in CI
quality: fmt-check lint types contracts test

dev:
    @echo "dev server arrives with the HTTP adapter"

doctor:
    uv run lookout --help
