# 0005. The LLM sits behind an OpenAI-compatible port

- Status: accepted
- Date: 2026-10-24

## Context

The model should be swappable: Ollama locally (free) first, a hosted model later, whichever is cheapest or best.
Ollama, OpenRouter, vLLM, LM Studio and the main hosted providers speak the OpenAI chat and embeddings protocol.

## Decision

`Enricher` and `Embedder` are ports. The single adapter speaks the OpenAI-compatible HTTP protocol through `httpx`
(base URL, model and key from configuration; Ollama at `http://localhost:11434/v1` by default) and asks for JSON
validated against a schema, with one repair retry. Calls are bounded: body truncated, timeouts, a daily call budget.
Responses can be recorded in cassettes for tests (ADR 0009).

## Consequences

Switching provider is a config change. No vendor SDK dependency. Models that cannot follow a JSON schema produce
retries; the doctor command checks the endpoint and the model.

## Alternatives considered

A vendor SDK per provider: more code, no gain. LiteLLM as a layer: extra moving part for one protocol.
