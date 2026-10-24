# 0013. Sources and channels live in the database and are edited in the dashboard

- Status: accepted
- Date: 2026-10-24

## Context

Sources and channels were read from `lookout.yaml`. Adding a feed meant editing a file and restarting, and the dashboard
could only switch a source on or off. The user wants to treat sources as rivers they plug in and channels as the places
they flow to, from the dashboard, and to see at once what a source is doing.

## Decision

- Sources and channels are stored in SQLite and edited through the API and the dashboard: add, change, delete.
- `lookout.yaml` **seeds** them once: when the table is empty at start, its `sources` and `channels` are copied in.
  After that the database is the truth and the file's lists are ignored (the guide says so; `doctor` does not warn).
- A source's `type` (rss, github, osv) says which settings it takes. The API publishes each type's fields so the
  dashboard can build the form, and a source is validated by building its fetcher: what would fail at run time fails
  when it is saved, with the same message.
- Fetchers and the channel catalogue are built from the database when a run starts, so a change applies to the next run
  without a restart.
- Deleting a source keeps its items. A channel cannot be deleted while a source feeds it; renaming is delete and create.
  `Other` cannot be deleted. Kinds, the stack and the rest of the configuration stay in the file.

## Consequences

The inbox can be rebuilt from the dashboard alone. A configuration file for a fresh install still works, and so does a
container image with no editing. Two places can describe sources (the seed file and the database), which the guide
explains. Source validation lives in one place, shared by the file seed and the form.

## Alternatives considered

The dashboard writing back to the YAML file: concurrent edits, lost comments, and a file the container mounts read-only.
Keeping the file as the only truth with a form that edits it: same problems. Both at once with a merge: hard to explain.
