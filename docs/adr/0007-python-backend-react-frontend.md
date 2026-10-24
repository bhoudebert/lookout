# 0007. Python backend, React frontend

- Status: accepted
- Date: 2026-10-24

## Context

Backend language: Rust was considered; Python was chosen to learn it well and for its feed, HTTP and data libraries.
The dashboard is an interactive inbox.

## Decision

Python 3.13 with `uv`, `ruff`, `pyright` strict, `pytest`, FastAPI for the HTTP adapter, Typer for the CLI. Frontend:
React, TypeScript strict, Vite, TanStack Query, tested with Vitest and Playwright. The frontend talks to the backend
through the HTTP API only, whose OpenAPI schema generates the TypeScript client types (checked for staleness in CI).
The backend serves the built frontend in production: one process, one container.

## Consequences

Two toolchains, both pinned by Nix. A typed contract between them.

## Alternatives considered

Rust backend: more performance than needed, slower to iterate. HTMX: less interactive for keyboard triage.
