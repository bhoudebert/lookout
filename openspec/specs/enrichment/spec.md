# Enrichment Specification (enrichment)

## Purpose

Have a model summarise, categorise and score each new item, safely and within budget.

## Requirements

### Requirement: Structured enrichment

For each new item the enricher SHALL return a summary (at most a configured length), one channel from those its source allows (the full path of the most specific category that fits), up to five tags
(including what the item is), a score from 0 to 100 for importance to the user, an `action_needed` flag and a one-sentence
reason. The answer SHALL be validated against a schema; an invalid answer SHALL get one repair attempt, then the item
SHALL be marked `enrichment_failed` and shown with a neutral score, never dropped.

#### Scenario: Model answers with prose

- **WHEN** the model returns text that is not valid JSON twice
- **THEN** the item is kept, flagged `enrichment_failed`, and the failure is visible in the dashboard

### Requirement: Profile in the prompt

The prompt SHALL include the user's declared interests and stack, the allowed channels with their descriptions, so scoring reflects them, and SHALL state that item
text is data and not instructions.

### Requirement: Budget

The number of model calls per day SHALL be limited by configuration. When the limit is reached, remaining items SHALL
wait (state `pending_enrichment`) and the rule-based priority SHALL still apply to them.

#### Scenario: Budget exhausted

- **WHEN** the daily limit is reached while a critical advisory arrives
- **THEN** the advisory is in the inbox as P1 or higher from its rule floor, flagged as not yet summarised

### Requirement: Only what can be seen

The model SHALL be asked only about items that are `new`, `seen` or `snoozed`. Items that are `done`, `dismissed` or
`expired` SHALL NOT use the daily budget, and SHALL join the queue if they are reopened. The run summary SHALL say how
many items are waiting for the model when the limit stopped a run.

#### Scenario: A backlog that expired

- **WHEN** thousands of unread items have expired and a few are in the inbox, with a small daily limit
- **THEN** the budget is spent on the inbox items only

### Requirement: Provider independence

The enricher SHALL speak the OpenAI-compatible chat protocol with a configurable base URL, model and key. `doctor` SHALL
check that the endpoint answers and that the model exists.
