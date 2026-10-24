# Enrichment Specification (enrichment)

## Purpose

Have a model summarise, categorise and score each new item, safely and within budget.

## Requirements

### Requirement: Structured enrichment

For each new item the enricher SHALL return a summary (at most a configured length), one kind from the configured list,
one channel from those its source allows, up to five tags, a score from 0 to 100 for importance to the user, an `action_needed` flag and a one-sentence
reason. The answer SHALL be validated against a schema; an invalid answer SHALL get one repair attempt, then the item
SHALL be marked `enrichment_failed` and shown with a neutral score, never dropped.

#### Scenario: Model answers with prose

- **WHEN** the model returns text that is not valid JSON twice
- **THEN** the item is kept, flagged `enrichment_failed`, and the failure is visible in the dashboard

### Requirement: Profile in the prompt

The prompt SHALL include the user's declared interests and stack, the allowed channels with their descriptions, the kinds, so scoring reflects them, and SHALL state that item
text is data and not instructions.

### Requirement: Budget

The number of model calls per day SHALL be limited by configuration. When the limit is reached, remaining items SHALL
wait (state `pending_enrichment`) and the rule-based priority SHALL still apply to them.

#### Scenario: Budget exhausted

- **WHEN** the daily limit is reached while a critical advisory arrives
- **THEN** the advisory is in the inbox as P1 or higher from its rule floor, flagged as not yet summarised

### Requirement: Provider independence

The enricher SHALL speak the OpenAI-compatible chat protocol with a configurable base URL, model and key. `doctor` SHALL
check that the endpoint answers and that the model exists.
