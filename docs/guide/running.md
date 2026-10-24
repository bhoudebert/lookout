# Running and scheduling

## One process

```sh
lookout serve --host 127.0.0.1 --port 8899
```

serves the API and the dashboard, and runs on `schedule.interval_minutes` (every 60 minutes by default; the first run comes after one interval, so press **Run now** once). There is no authentication: keep it on `127.0.0.1`, or put it behind a reverse proxy that authenticates.

## From the terminal

```sh
lookout run          # fetch and read now
lookout inbox -p P0 -p P1
lookout act <id> done
lookout export > backup.jsonl
```

See the [command reference](/reference/commands).

## One run at a time

A run started while another is in progress does not start a second one; the dashboard shows the running one. A run that crashes is reported, never silent, and items that were stored but not read are read by the next run, so an interrupted run loses nothing.

## Backups and upgrades

Everything is in the SQLite file. Schema changes are applied on start, one transaction per step, with a copy of the file (`lookout.db.bak-vN`) written before. A database from a newer Lookout is refused without being touched.
