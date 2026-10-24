# Roadmap and ideas

Not commitments. Ordered by expected value for one person tracking the news, releases and risks of their own stack.

## Now (v0.x)

- Core: sources, enrichment, priority, triage, personalization (see `openspec/specs/`).
- Adapters: RSS/Atom, Hacker News, Reddit, GitHub releases, GitHub advisories and Dependabot alerts, OSV and NVD.
- Dashboard, guide, website.

## Next

- YouTube (channel feed plus transcript) and website-change watch.
- Digest by email or Telegram for P0/P1, with quiet hours.
- Stack discovery from lockfiles of the watched repositories.
- Duplicate clustering across sources (same story on HN, Reddit and a blog) with embeddings.

## Later

- Podcasts, newsletters by IMAP, Mastodon lists.
- Multi-user with a registry and one SQLite file each, as in agentRide ADR 0027.
- Recorded-cassette evals for the enrichment prompt, replayed free in CI.
