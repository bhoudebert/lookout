# Roadmap and ideas

Not commitments. Ordered by expected value for one person tracking the news, releases and risks of their own stack.

## Done (v0.x)

- Core: RSS/Atom ingestion, enrichment through any OpenAI-compatible model, priority rules, triage, personalization.
- CLI, HTTP API, dashboard, user guide and website.
- GitHub releases, advisories and Dependabot alerts, through `gh` or a token.

## Now

- OSV and NVD adapters, with version-range matching against the declared stack, so advisories for packages you use
  arrive from repositories you do not watch.
- Dedicated Hacker News and Reddit adapters (scores, comment counts).
- Container image and a NixOS module.

## Next

- YouTube (channel feed plus transcript) and website-change watch.
- Digest by email or Telegram for P0/P1, with quiet hours.
- Stack discovery from lockfiles of the watched repositories.
- Duplicate clustering across sources (same story on HN, Reddit and a blog) with embeddings.

## Later

- Podcasts, newsletters by IMAP, Mastodon lists.
- Multi-user with a registry and one SQLite file each, as in agentRide ADR 0027.
- Recorded-cassette evals for the enrichment prompt, replayed free in CI.
