# Source Management Specification (source-management)

## Purpose

Plug in, change and unplug sources and channels from the dashboard, without editing a file or restarting.

## Requirements

### Requirement: Seeded once

When Lookout starts and no source is stored, the sources of the configuration file SHALL be stored; the same holds for
channels. After that the stored ones are the truth and the file's lists SHALL NOT change them.

#### Scenario: Edited file after the first start

- **WHEN** a source is added to `lookout.yaml` after the first start
- **THEN** it does not appear; sources are added in the dashboard

### Requirement: Sources

The user SHALL be able to add a source (name, type, the settings its type takes, channels, keywords, a model of its own, enabled), change
any of it except the name, switch it on and off, and delete it. Names SHALL be unique, ignoring case. The dashboard SHALL
learn from the API which types exist and which fields each takes, and build its form from that.

#### Scenario: Invalid settings

- **WHEN** an RSS source is saved with an address that is not http or https
- **THEN** it is refused with a message naming the field, and nothing is stored

#### Scenario: A new source is used at once

- **WHEN** a source is added and a run starts
- **THEN** that run fetches it, with no restart

### Requirement: Deleting a source

Deleting a source SHALL keep its items and its history of runs SHALL be forgotten; the items keep their source name.

### Requirement: Channels

The user SHALL be able to add a channel (name, description), change its description, and delete it. A channel SHALL NOT
be deleted while a source feeds it, and the refusal SHALL name those sources. `Other` SHALL always exist and SHALL NOT be
deleted. A source SHALL only list channels that exist.

### Requirement: Where the items go

The source form SHALL say, for the categories ticked, what will happen: none, the model chooses a category for each item
among all of them (using the model limit, `Other` when none fits); one, every item goes there without asking the model;
several, the model chooses among them. The form SHALL let the user create a category (a name, optionally a description)
without leaving it, and tick it; a refusal SHALL be shown and keep what was typed.

### Requirement: Suggested sources

The sources page SHALL suggest well-known sources that are not yet there (by name or by feed address), grouped by theme
(link sites, a language, AI, security, service status, Reddit communities, YouTube channels, news, deals), each theme
collapsed and shown only while it has a suggestion left, each suggestion added with one click. A suggestion that files in a category SHALL create that category first when it does not exist. A refusal
SHALL be shown and leave the suggestion available.

### Requirement: Applies to the next run

Changes to sources and channels SHALL apply to the next run; a run in progress is not affected.

### Requirement: Same checks as the file

A source from the file and a source from the form SHALL pass the same validation, with the same messages.
