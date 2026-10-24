# Troubleshooting

Start with `lookout doctor`: one line per check, with the reason and a hint, and a non-zero exit if anything fails.

## "Is Ollama running?"

The model endpoint refused the connection. Start it with `ollama serve`. If doctor says the endpoint answers but has no model, run the `ollama pull` it suggests.

## Items stay "waiting for the model"

Either the daily limit is spent (`llm.daily_limit`; they continue tomorrow, and rule-based priorities already apply) or the model is down. `lookout run` prints how many items are waiting.

## "The model could not read it"

The model answered twice without valid JSON. Small models struggle with the format; try a larger one. The item stays in the inbox with a neutral priority.

## A source shows an error

The Sources page and `lookout doctor` show the last error. Lookout retries with growing delays; fix the URL or wait. A page that is not a feed is reported as such.

## "Cannot reach Lookout" in the dashboard

`lookout serve` is not running, or you opened a different port.

## The dashboard is blank or 404 on `/`

The dashboard is not built. Run `npm run --prefix frontend build`, or point `dashboard_dir` at the built files.

## A priority looks wrong

Open the item: **Why this rank** shows the rule or score behind it. If a rule should have applied, check the item names a package in your `stack` (whole word, or an alias), then run `lookout reassess`. To report a wrong model reading, open an "Eval case" issue.
