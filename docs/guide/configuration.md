# Configuration

Lookout reads `lookout.yaml` (override with `--config` or `LOOKOUT_CONFIG`). Start from `lookout.example.yaml`. Errors name the file, the key and the expected form.

Secrets never go in the file: set `LOOKOUT_LLM_API_KEY` in the environment if your endpoint needs a key. `LOOKOUT_DATABASE` and `LOOKOUT_DASHBOARD_DIR` give defaults for `database` and `dashboard_dir` (the container image sets them); a key in the file wins.

## Keys

`channels` (your categories) and `sources` only **seed** the dashboard on the first start (see [sources](/sources) and [categories](/concepts)); everything else below is read at every start.

| Key               | Default                                          | What                                                                                                                                                                                                                                                                                                                        |
| ----------------- | ------------------------------------------------ | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `database`        | `data/lookout.db`                                | The SQLite file. A copy is the whole backup.                                                                                                                                                                                                                                                                                |
| `llm`             | Ollama on localhost                              | `base_url`, `model`, `daily_limit` (model calls per day, default 200; with a local model that costs nothing, raise it, for example to 2000), `summary_chars` (default 400).                                                                                                                                                 |
| `digest`          | follows `llm`                                    | The model that writes [digests](/digest): `model`, `base_url` (empty means the `llm` ones), `max_items` (default 200), `context_chars` (default 40000, what one call may read), `max_answer_tokens` (default 6144, a model that reaches it fails the digest) and `reasoning_effort` (default `none`, empty to not send it). |
| `interests`       | empty                                            | A sentence told to the model so scores reflect you.                                                                                                                                                                                                                                                                         |
| `channels`        | only `Other`                                     | The **topics** you look at, each with a `name`, a one-line `description` the model uses and an optional `icon` (one emoji; without it the model suggests one). `Other` always exists. See [channels](/concepts).                                                                                                            |
| `stack`           | empty                                            | What you depend on: `name`, optional `ecosystem`, `aliases` and `version` (quote it). Drives the [priority rules](/priorities).                                                                                                                                                                                             |
| `thresholds`      | p0 90, p1 70, p2 40                              | Lowest score of each band. Must satisfy p0 > p1 > p2.                                                                                                                                                                                                                                                                       |
| `retention`       | 30, 30 days; expiry p0 never, p1 30, p2 14, p3 7 | How long things stay (see [keeping the inbox small](/inbox-size)): `max_age_days` (entries older than this are not stored, per source override), `rules_window_days` (older items get no rule floor) and `expire_after_days` per level `p0` to `p3` (0 = never).                                                            |
| `personalization` | 30 days, 5 signals                               | `half_life_days` and `minimum_signals`. See [personalization](/personalization).                                                                                                                                                                                                                                            |
| `github`          | `auto`                                           | `via`: `auto` (your `gh` login if you have one, else `LOOKOUT_GITHUB_TOKEN` or `GITHUB_TOKEN`), `gh` or `token`. See [sources](/sources).                                                                                                                                                                                   |
| `schedule`        | 60                                               | `interval_minutes` between runs while serving; `0` turns the schedule off.                                                                                                                                                                                                                                                  |
| `dashboard_dir`   | `frontend/dist`                                  | The built dashboard that `lookout serve` serves.                                                                                                                                                                                                                                                                            |
| `body_limit`      | 4000                                             | Characters of an item's text kept and sent to the model.                                                                                                                                                                                                                                                                    |
| `sources`         | empty                                            | See [sources](/sources).                                                                                                                                                                                                                                                                                                    |

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
