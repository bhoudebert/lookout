# 0008. Nix from day one

- Status: accepted
- Date: 2026-10-24

## Context

The project spans Python, Node and system tools. The owner runs NixOS. Reproducible environments avoid "works on my
machine", and CI should run exactly what developers run.

## Decision

A flake (flake-parts, one module per concern under `nix/modules`) provides the dev shell (Python, uv, Node, just, gh,
sqlite, Playwright browsers), apps (`nix run .#quality`, `.#dev`, `.#doctor`), a container image and a NixOS module
for self-hosting. Git hooks are installed by the shell. CI installs Nix and runs `nix run .#quality`. Python
dependencies are locked by `uv.lock`, Node by `package-lock.json`; native wheels get their libraries through
`LD_LIBRARY_PATH` in the shell (no nix-ld required).

## Consequences

One command reproduces CI. Contributors without Nix can follow the manual setup in `CONTRIBUTING.md`. Nix evaluation
adds some CI time, mitigated by a cache.

## Alternatives considered

Docker dev containers: heavier locally. Plain `uv` and `nvm`: not reproducible across machines.
