# 0003. Hexagonal architecture, enforced by import contracts

- Status: accepted
- Date: 2026-10-24

## Context

Many adapters (sources, LLMs, stores, entry points) will come and go. The domain must stay stable, testable without
I/O, and independent of any framework.

## Decision

Packages `domain`, `application`, `adapters`, `bootstrap` under `src/lookout/`. Ports are `typing.Protocol`s in
`application/ports`. `import-linter` contracts (layers plus an independence contract between adapter packages) run in
the gate and fail the build on a violation. The domain uses frozen dataclasses and value objects; use cases are small
classes taking ports in their constructor.

## Consequences

Adding a source is one adapter and one config entry. Tests swap adapters for fakes. The rules are checked by a tool, not
by review. Slightly more files than a flat layout.

## Alternatives considered

A flat module layout: fastest to start, erodes. A framework-centric layout (FastAPI everywhere): couples logic to HTTP.
