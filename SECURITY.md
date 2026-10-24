# Security

## Secrets

`.env` holds API keys and tokens (LLM provider, GitHub) and is git-ignored. Never commit it. GitHub access prefers the
local `gh` login, so no token needs to be stored on a laptop.

## What Lookout reaches

Only what you configure: the source URLs and APIs in your watchlist, the GitHub API (through `gh` or a token), and the
LLM endpoint you set (Ollama on localhost by default). Content fetched from sources is data, never instructions: the
prompts say so, and the code enforces priority floors whatever the model reads (ADR 0002).

## Reporting

Open a private security advisory on the repository, or contact the maintainer directly. Please do not open a public
issue for a vulnerability.
