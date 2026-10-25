# CLI Specification (cli)

## Purpose

Operate Lookout from a terminal.

## Requirements

### Requirement: Commands

`lookout serve` (API, UI, scheduler), `lookout run` (one run now), `lookout doctor`, `lookout inbox` (list with
filters), `lookout act <id> <seen|done|snooze|star>`, `lookout rate <id> <up|down|none>`, `lookout demo` (seed demo data), `lookout export`
(JSON). Every command SHALL have `--help`.

### Requirement: Configuration

Configuration SHALL be read from `lookout.yaml` (path overridable by `--config` or `LOOKOUT_CONFIG`), secrets from the
environment. Errors SHALL name the file, the key and the expected form.

### Requirement: Doctor

`lookout doctor` SHALL check the configuration, the database and its migration state, the LLM endpoint and model, GitHub
access and each source, printing one line per check with a clear failure reason and exiting non-zero on failure.

#### Scenario: Ollama not running

- **WHEN** the LLM endpoint refuses connections
- **THEN** doctor prints the endpoint, the error and a hint to start Ollama, and exits with status 1
