# Configuration

Lookout reads `lookout.yaml` (override with `--config` or `LOOKOUT_CONFIG`). Start from `lookout.example.yaml`. Errors name the file, the key and the expected form.

Secrets never go in the file: set `LOOKOUT_LLM_API_KEY` in the environment if your endpoint needs a key.

## Keys

| Key               | Default                                                          | What                                                                                                                                      |
| ----------------- | ---------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------- |
| `database`        | `data/lookout.db`                                                | The SQLite file. A copy is the whole backup.                                                                                              |
| `llm`             | Ollama on localhost                                              | `base_url`, `model`, `daily_limit` (model calls per day, default 200), `summary_chars` (default 400).                                     |
| `interests`       | empty                                                            | A sentence told to the model so scores reflect you.                                                                                       |
| `categories`      | security, release, breaking-change, tooling, ai, industry, other | The categories the model must choose from.                                                                                                |
| `stack`           | empty                                                            | What you depend on: `name`, optional `ecosystem` and `aliases`. Drives the [priority rules](/priorities).                                 |
| `thresholds`      | p0 90, p1 70, p2 40                                              | Lowest score of each band. Must satisfy p0 > p1 > p2.                                                                                     |
| `personalization` | 30 days, 5 signals                                               | `half_life_days` and `minimum_signals`. See [personalization](/personalization).                                                          |
| `github`          | `auto`                                                           | `via`: `auto` (your `gh` login if you have one, else `LOOKOUT_GITHUB_TOKEN` or `GITHUB_TOKEN`), `gh` or `token`. See [sources](/sources). |
| `schedule`        | 60                                                               | `interval_minutes` between runs while serving; `0` turns the schedule off.                                                                |
| `dashboard_dir`   | `frontend/dist`                                                  | The built dashboard that `lookout serve` serves.                                                                                          |
| `body_limit`      | 4000                                                             | Characters of an item's text kept and sent to the model.                                                                                  |
| `sources`         | empty                                                            | See [sources](/sources).                                                                                                                  |

## Using another model

Any OpenAI-compatible endpoint works:

```yaml
llm:
  base_url: https://openrouter.ai/api/v1
  model: anthropic/claude-haiku-5-5
  daily_limit: 100
```

```sh
export LOOKOUT_LLM_API_KEY=...
```

Then check it with `lookout doctor`.
