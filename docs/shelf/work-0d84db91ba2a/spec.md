# Spec: GitHub badges on the README

Round 1 changes: the round narrative is gone; the pull request and commit requirements moved to a separate "Delivery"
section (section 3) and the quality-gate requirement is dropped; the exact badge URLs are now written out; the Pages
badge is kept and its stale or empty state is a scenario; the "like agent-motoride" limit is stated in the goal; the
README-unchanged requirement is checked by a `git diff` rule.

## 1. Goal

I want a row of GitHub badges at the top of `README.md`, right under the title, so the state of the project is visible at
a glance: CI, docs site, release pipeline, licence, latest release and container image. The reference
`bhoudebert/agent-motoride` could not be read from here, so "like agent-motoride" is **not** verified: the set below is
the usual one for the workflows this repository has, and I add nothing that needs an external account.

## 2. Requirements (the README)

Let `R = bhoudebert/lookout`. Today the README has no badges: line 1 is `# Lookout`, line 3 is the description.

1. The README SHALL show one badge block directly after the `# Lookout` title, separated by a blank line from the title
   and from the description paragraph that follows.
2. The block SHALL contain exactly these three workflow badges, and no other workflow badge. Image URL is
   `https://github.com/R/actions/workflows/<file>/badge.svg?branch=main`:
   - CI: `ci.yml`, linking to `https://github.com/R/actions/workflows/ci.yml`;
   - Pages: `pages.yml`, linking to the published site `https://bhoudebert.github.io/lookout/`;
   - Release: `release.yml`, linking to `https://github.com/R/actions/workflows/release.yml`. It runs on every push to
     `main`, so it shows whether release-please is healthy; it is not a quality signal.

   `image.yml` (only `pull_request` and `workflow_dispatch`) and `pr-title.yml` (pull requests only) SHALL NOT get a
   badge: on `main` they have no run and would read "no status".
3. The block SHALL contain a licence badge: image `https://img.shields.io/github/license/R`, link
   `https://github.com/R/blob/main/LICENSE`. `LICENSE` is MIT text today.
4. The block SHALL contain a latest-release badge: image `https://img.shields.io/github/v/release/R`, link
   `https://github.com/R/releases`.
5. The block SHALL contain a container badge: a static shields image
   `https://img.shields.io/badge/ghcr.io-bhoudebert%2Flookout-blue?logo=docker`, link
   `https://github.com/R/pkgs/container/lookout`. The label is static, so it never depends on a run. (`release.yml`
   pushes `ghcr.io/${{ github.repository }}`, which is that package.)
6. Every badge SHALL be a Markdown image wrapped in a link, with non-empty alt text naming it (CI, Pages, Release,
   License, Latest release, Container image).
7. Every `github.com` or `img.shields.io/github/...` path in the block SHALL begin with `R` (the query string
   `?branch=main` does not count as path). The only other hosts allowed are `img.shields.io/badge/...` (Req 5) and
   `bhoudebert.github.io/lookout/` (Req 2).
8. Badges SHALL come from GitHub or shields.io only: no other service, account, token or secret.
9. The change SHALL touch only `README.md` and the files under `docs/shelf/work-0d84db91ba2a/`. No code, workflow or
   config file changes.
10. The README SHALL differ from `main` by added lines only: `git diff -U0 main -- README.md` shows no removed line,
    and every added line sits between line 1 and the first line of the description paragraph.

## 3. Delivery (the pull request, not the README)

11. The pull request title SHALL follow Conventional Commits as `pr-title.yml` checks it. For this work:
    `docs(readme): add status badges`.
12. New commits SHALL carry no attribution trailer (`AGENTS.md` rule 9), even where the harness suggests one, and SHALL
    pass the commitlint rules of `AGENTS.md` rule 2. The already-pushed `chore(shelf): intake` commits SHALL be checked
    with `just commits <base sha>`; if any fails, that is escalated to the maintainer, not fixed by rewriting history.

## 4. Scenarios

- Req 1: WHEN the README is opened THEN line 1 is `# Lookout`, line 2 blank, the badge block follows, then a blank
  line, then "A self-hosted watch tower...". Edge: no badge sits after the description.
- Req 2: WHEN the workflow badges are listed THEN they are exactly `ci.yml`, `pages.yml`, `release.yml`, each image URL
  ending `badge.svg?branch=main`. Edge: no `image.yml` or `pr-title.yml` badge. Edge: each `<file>.yml` exists in
  `.github/workflows/` (a rename would break the badge).
- Req 2 (Pages): WHEN no `pages.yml` run exists on `main`, or the last matching one is old, THEN the Pages badge may read
  "no status" or an old result. `pages.yml` has a `paths` filter (`site/**`, `docs/**`, ...), so a README-only merge does
  not rerun it. Acceptable, not an error. Note: this work's documents live under `docs/`, so merging this pull request
  does match the filter and should produce a run.
- Req 3: WHEN the licence badge is clicked THEN it opens `blob/main/LICENSE`. Edge: `grep -c MIT LICENSE` is above 0.
- Req 4: WHEN no release exists yet THEN shields shows "no releases"; acceptable.
- Req 5: WHEN the container badge is clicked THEN it opens the package page. Edge: if the package is not published the
  page 404s while the badge still renders.
- Req 6: WHEN images fail to load THEN the alt text still names each badge. Edge: no alt text is empty.
- Req 7: WHEN every URL is listed THEN each GitHub or shields `github/` path starts with `bhoudebert/lookout`, and none
  contains `agent-motoride` or another owner.
- Req 8: WHEN hosts are listed THEN each is `github.com`, `img.shields.io` or `bhoudebert.github.io`.
- Req 9: WHEN `git diff --stat main` is read THEN only `README.md` and `docs/shelf/work-0d84db91ba2a/*` appear.
- Req 10: WHEN `git diff -U0 main -- README.md` is read THEN it has no `-` line and one added hunk starting right after
  line 1. Edge: a re-wrapped description line shows up as a removal and fails.
- Req 11: WHEN the title is `docs(readme): add status badges` THEN `PR title` is green. Edge: `Add badges` (no type) or
  a header over 100 characters fails.
- Req 12: WHEN `just commits <base>` runs on the branch THEN it exits 0. Edge: if an intake commit fails, the builder
  stops and reports it; no force-push, no history rewrite.

## 5. Out of scope

- Coverage, code-quality or download-count badges (need an external account).
- Python, Node or Nix version badges.
- Badges in the guide, `site/` or docs pages.
- Changing workflows to improve a badge (for example a `push` trigger on `image.yml`).
- Translating or restructuring the README.
- Investigating why CI was red in a previous round: that belongs in the plan, and a red step is fixed at its cause
  (`AGENTS.md` rules 4 and 8), never skipped.

## 6. Conflicts with existing specs

None. No file in `openspec/specs/` or `docs/adr/` covers README content. `AGENTS.md` asks to update the README when the
overview changes; this is presentational. Commit type is `docs` (ADR 0010). `AGENTS.md` rule 9 forbids attribution
trailers; Req 12 follows it over the harness suggestion. `release-please` default versioning bumps only on `feat` and
`fix`, so I expect no release from a `docs` commit alone (not run).

## 7. Open questions

- Is `bhoudebert/lookout` public? If private, workflow, release and package badges render broken for anonymous visitors.
  Does not change the design.
- Is a package published at `ghcr.io/bhoudebert/lookout`? Not confirmed. If not, drop Req 5; nothing else depends on it.
- Does the owner want the exact `agent-motoride` set? It is unseen; a badge needing an external account would be a
  design change.
