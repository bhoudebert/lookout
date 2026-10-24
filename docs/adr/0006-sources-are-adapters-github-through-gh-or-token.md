# 0006. Sources are adapters; GitHub goes through `gh` or a token

- Status: accepted
- Date: 2026-10-24

## Context

Sources differ (feeds, JSON APIs, pages). GitHub needs authentication for security data (Dependabot alerts), and on a
laptop the user is already logged in with `gh`.

## Decision

Each source kind is a `SourceFetcher` adapter declared in `lookout.yaml` (`kind: rss`, `kind: hn`, `kind:
github`, …). Repository data goes through a `GitHubGateway` port with two adapters: the local `gh` executable
(reuses the user's login, no stored token) and REST over `httpx` with a token for servers. The watchlist is declared,
not discovered. Fetchers return raw items with a stable external id; dedupe and enrichment are not their job. Feeds and
APIs are preferred over scraping.

## Consequences

Adding a source touches one adapter, one config schema entry, one fixture and one spec scenario. The `gh` adapter is
tested against a fake executable.

## Alternatives considered

Only a token: needs secret handling on laptops. A GitHub App: heavy for one user.
