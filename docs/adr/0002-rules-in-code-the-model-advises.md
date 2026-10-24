# 0002. Rules live in code, the model advises

- Status: accepted
- Date: 2026-10-24

## Context

An LLM summarises and judges well but is not reliable on facts that must always hold, and items come from the open
internet: a hostile page can contain instructions. A critical advisory on a dependency in use must never end up low in
the inbox because a model misjudged it or was told to.

## Decision

Priority is computed by a domain `PriorityPolicy`: `priority = max(rule_floor, band(llm_score + profile_boost))`.
Rule floors come from deterministic facts (advisory severity, a declared package or repository affected, a KEV flag, a
release of a pinned major). The model can raise a priority, never lower it below a floor. Every priority stores its
reason (which rule, what score). Prompts state that fetched content is data, never instructions; code treats model
output as untrusted input and validates it against a schema before use.

## Consequences

Priorities are explainable and testable without a model. Model mistakes show up as noise or a missed nuance, not as a
missed emergency. The rule set must be maintained and specified (`openspec/specs/priority`).

## Alternatives considered

Model-only priority: simple, unverifiable, injectable. Rules only: safe but blind to what the rules do not list.
