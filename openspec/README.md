# Specifications

`specs/<capability>/spec.md` describes what the system does, as requirements with scenarios. `changes/` holds
proposals that add or modify requirements before they are implemented; once merged into the code, the change is folded
into the specs and its folder moves to `changes/archive/` (dated), kept as the record of how it was decided.

| Capability       | Covers                                                                                     |
| ---------------- | ------------------------------------------------------------------------------------------ |
| source-ingestion | Declared sources, fetchers, normalisation, dedupe, failures, politeness                    |
| enrichment       | Summary, category, tags, score and action flag from the LLM; schema validation; budget     |
| priority         | P0-P3 from rule floors and the model score, with a recorded reason                         |
| triage           | Item states, transitions, snooze, star, undo; the inbox query                              |
| personalization  | Feedback signals, profile, ranking inside a priority band, the "why this rank" explanation |
| stack-watch      | The declared stack and watchlist, matching items to it                                     |
| github-sources   | Releases, advisories and Dependabot alerts through `gh` or a token                         |
| dashboard        | The web inbox: lists, filters, detail, shortcuts, source management                        |
| scheduling       | Periodic runs, run records, quiet failure handling                                         |
| cli              | `lookout serve`, `run`, `doctor`, `export`, configuration loading                          |
