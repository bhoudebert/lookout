# Scheduling Specification (scheduling)

## Purpose

Keep the inbox fresh without the user.

## Requirements

### Requirement: Periodic runs

A run SHALL fetch each enabled source at its interval (default per kind), then enrich new items. Runs SHALL be
triggerable by hand from the API and the CLI.

### Requirement: Run records

Each run SHALL store start, end, per-source counts (fetched, new, failed) and the model calls used.

### Requirement: No overlap

Two runs SHALL NOT overlap; a trigger during a run SHALL return the running run.

#### Scenario: Double trigger

- **WHEN** a run is triggered while one is in progress
- **THEN** no second run starts and the response identifies the running one

### Requirement: Resumable

Items stored but not yet enriched SHALL be enriched by the next run, so an interrupted run loses nothing.
