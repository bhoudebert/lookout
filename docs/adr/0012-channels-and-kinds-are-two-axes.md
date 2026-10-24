# 0012. Channels and kinds are two axes, set by the source and refined by the model

- Status: accepted
- Date: 2026-10-24

## Context

Items were sorted by one "category". The user thinks in two ways at once: **what it is about** (AI, Rust, Security,
Other: where they want to look) and **what it is** (an LLM release, an API change, a schedule, a security fix: how
urgent and how actionable). A feed already says a lot about both: its own topic, its tags, its author.

## Decision

Two independent axes plus tags.

- A **channel** is a topic the user defines (name and a one-line description for the model), with `Other` always there.
  A source lists the channels it may feed. One channel: its items are filed there and the model is not asked. Several,
  or none (any): the model picks one of them. An item never leaves its source's channels.
- A **kind** is what the item is, from a list the user can edit (default: release, security, api-change, deprecation,
  announcement, schedule, tutorial, research, outage, discussion, other). The model picks exactly one. This replaces the
  former "category".
- **Tags** are free. The article's own tags and its author are kept as facts from the source; the model adds its own.
- The **author** is a fact from the source, kept per item and learnt from like a source (ADR 0011, personalization).

Facts from sources (author, feed tags, channel of a single-channel source) are never overwritten by the model.

## Consequences

The inbox filters by channel and by kind independently. Personalization has more features to learn from (source,
author, channel, kind, tag). The model's task stays a closed choice, easy to validate. The database is migrated
(`category` becomes `kind`, `channel` and `author` are added) by a versioned step, which is the first real use of the
migration machinery.

## Alternatives considered

One taxonomy with both topics and types mixed: the user's own example (AI, Rust next to LLM, API, Schedule) shows they
are different questions. Letting the model invent channels: unreviewable and unstable between runs. Tags only: no way to
say "Rust is a place I look".
