# Roadmap and ideas

Not commitments. Ordered by expected value for one person tracking the news, releases and risks of their own stack.

## Done (v0.x)

- Core: RSS/Atom ingestion, enrichment through any OpenAI-compatible model, priority rules, triage, personalization.
- CLI, HTTP API, dashboard, user guide and website.
- GitHub releases, advisories and Dependabot alerts, through `gh` or a token.
- Sources and channels managed in the dashboard, with a file that only seeds them.
- OSV vulnerabilities for the declared stack, with CVSS severity and CISA's known-exploited flag.
- A container image (published with each release) and a NixOS module, see the self-hosting guide.

## Now

- Rate an item's priority by hand and learn from it, then put similar rated items into the model's prompt (embeddings).
- Website-change watching and a YouTube transcript source.
- Dedicated Hacker News and Reddit adapters (scores, comment counts).

## Next

- YouTube (channel feed plus transcript) and website-change watch.
- Digest by email or Telegram for P0/P1, with quiet hours.
- Stack discovery from lockfiles of the watched repositories.
- Duplicate clustering across sources (same story on HN, Reddit and a blog) with embeddings.

## Later

- Podcasts, newsletters by IMAP, Mastodon lists.
- Multi-user with a registry and one SQLite file each, as in agentRide ADR 0027.
- Recorded-cassette evals for the enrichment prompt, replayed free in CI.
