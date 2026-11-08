# Spec: GitHub badges on the README, and a green CI quality gate

Round 0 feedback ("fix the CI quality gates !!") changed this spec: a new requirement block (section 3) makes a green
`Quality gate` job part of the work; the earlier "touch only README.md and the work documents" limit now has an
exception for the cause of a red step; the "investigating CI is out of scope" line is removed.

Re-checked this round: no shell and no CI log were available again, so the red step is still unidentified. Read directly
instead: `commitlint.config.mjs` (header 100, body line 120, kebab-case scope) and `.prettierignore` (does not exclude
`docs/shelf/`); no line of `request.md` or `spec.md` exceeds 120 columns; all workflows use the same action major
versions (`checkout@v7`, `upload-artifact@v7`), so a version typo is less likely than a gate step.

## 1. Goal

I want a row of GitHub badges at the top of `README.md`, right under the title (CI, docs site, release pipeline,
licence, latest release, container image), and I want the CI quality gate of this branch to pass, so the CI badge is
green when this is merged. The reference `bhoudebert/agent-motoride` could not be read from here, so "like
agent-motoride" is **not** verified: the set below is the usual one for the workflows this repository has, and I add
nothing that needs an external account.

## 2. Requirements: the README

Let `R = bhoudebert/lookout`. Today the README has no badges: line 1 is `# Lookout`, line 3 is the description.

1. The README SHALL show one badge block directly after the `# Lookout` title, separated by a blank line from the title
   and from the description paragraph that follows.
2. The block SHALL contain exactly these three workflow badges and no other. Image URL is
   `https://github.com/R/actions/workflows/<file>/badge.svg?branch=main`:
   - CI: `ci.yml`, linking to `https://github.com/R/actions/workflows/ci.yml`;
   - Pages: `pages.yml`, linking to `https://bhoudebert.github.io/lookout/`;
   - Release: `release.yml`, linking to `https://github.com/R/actions/workflows/release.yml` (it runs on every push to
     `main`; it shows release-please health, not quality).

   `image.yml` and `pr-title.yml` SHALL NOT get a badge: they never run on `main`, so they would read "no status".

3. The block SHALL contain a licence badge: image `https://img.shields.io/github/license/R`, link
   `https://github.com/R/blob/main/LICENSE`.
4. The block SHALL contain a latest-release badge: image `https://img.shields.io/github/v/release/R`, link
   `https://github.com/R/releases`.
5. The block SHALL contain a container badge: static image
   `https://img.shields.io/badge/ghcr.io-bhoudebert%2Flookout-blue?logo=docker`, link
   `https://github.com/R/pkgs/container/lookout`.
6. Every badge SHALL be a Markdown image wrapped in a link, with non-empty alt text (CI, Pages, Release, License,
   Latest release, Container image).
7. Every `github.com` or `img.shields.io/github/...` path in the block SHALL begin with `R`. The only other hosts
   allowed are `img.shields.io/badge/...` (Req 5) and `bhoudebert.github.io/lookout/` (Req 2). No other service,
   account, token or secret.
8. The README SHALL differ from `main` by added lines only, all between line 1 and the description paragraph
   (`git diff -U0 main -- README.md` shows no removed line).

## 3. Requirements: the CI quality gate

The `Quality gate` job in `.github/workflows/ci.yml` runs `nix run .#quality` (`just quality`: `fmt-check`, `lint`,
`types`, `contracts`, `test`, `api-check`, `docs`, `ui-lint`, `ui-types`, `ui-test`, `e2e`), then the NixOS module
build, then, on pull requests, `just commits <base>`. The CI log of the failing run was not available to me, so the
failing step is **not identified**; the builder reads it first.

9. Every step of the `Quality gate` job SHALL pass on this branch: the gate, the NixOS module build and, on the pull
   request, the commit-message check. A red step is fixed at its cause (`AGENTS.md` rules 4 and 8): no skipped or
   deleted test, no lowered coverage threshold, no step removed or made non-blocking, no `--admin` merge.
10. The failing step and its cause SHALL be named in the pull request ("what was verified, what was not").
11. `just fmt-check` SHALL pass on every file this work adds or changes. `.prettierignore` does not exclude
    `docs/shelf/`, so `prettier --check .` (120 columns, `proseWrap: preserve`) also checks `README.md` and the work
    documents `request.md` and `spec.md`. They are the first suspects, together with the pushed intake commits.
12. `just commits <base sha>` SHALL exit 0 on the whole branch, including the `chore(shelf): intake` commits already
    pushed (header at most 100 characters, kebab-case scope, body lines at most 120). New commits carry no attribution
    trailer (`AGENTS.md` rule 9), even where the harness suggests one. If an already-pushed commit fails, the builder
    reports it to the maintainer; no history rewrite or force-push.
13. A fix SHALL touch only the files its cause requires, and SHALL be its own commit with its own Conventional Commits
    type (`fix`, `style`, `ci`, `build` or `test`, whichever is true), separate from the README commit
    (`docs(readme): add status badges`).
14. If the cause is a workflow or environment problem the repository cannot fix (a secret, a runner, an action version
    that does not exist), the builder SHALL stop and report it instead of working around it.

## 4. Scenarios

- Req 1: WHEN the README is opened THEN line 1 is `# Lookout`, line 2 blank, the badge block, a blank line, then "A
  self-hosted watch tower...". Edge: no badge after the description.
- Req 2: WHEN the workflow badges are listed THEN they are exactly `ci.yml`, `pages.yml`, `release.yml`, each ending
  `badge.svg?branch=main`. Edge: no `image.yml` or `pr-title.yml` badge; each file exists in `.github/workflows/`.
  Edge: `pages.yml` has a `paths` filter, so with no run on `main` the Pages badge may read "no status"; acceptable.
- Req 3: WHEN the licence badge is clicked THEN it opens `blob/main/LICENSE`. Edge: `LICENSE` contains "MIT".
- Req 4: WHEN no release exists THEN shields shows "no releases"; acceptable.
- Req 5: WHEN the package is not published THEN the badge renders and the link 404s; acceptable.
- Req 6: WHEN images fail to load THEN alt text names each badge. Edge: no alt text is empty.
- Req 7: WHEN every URL is listed THEN each github path starts with `bhoudebert/lookout`; none contains
  `agent-motoride`; hosts are only `github.com`, `img.shields.io`, `bhoudebert.github.io`.
- Req 8: WHEN `git diff -U0 main -- README.md` is read THEN there is no `-` line and one added hunk after line 1. Edge:
  a re-wrapped description line shows as a removal and fails.
- Req 9: WHEN CI runs on the pull request THEN `Quality gate` is green, including the commit check. Edge: the gate
  passing but `nix build .#checks.x86_64-linux.nixos-module` failing still counts as red.
- Req 10: WHEN the pull request is read THEN it names the step that was red and why. Edge: "CI is green now" without a
  cause fails.
- Req 11: WHEN `npx prettier --check README.md docs/shelf` runs THEN it exits 0. Edge: a `*` bullet, a bad nested-list
  indent or a trailing space in `spec.md` fails the whole gate at `fmt-check`, before any test runs.
- Req 12: WHEN `just commits <base>` runs THEN it exits 0. Edge: a trailer-bearing or over-long header on any commit
  fails it; the builder stops and reports.
- Req 13: WHEN `git log` of the branch is read THEN the README change and each CI fix are separate commits with
  different types. Edge: a fix for a coverage miss adds tests, it never lowers the gate.
- Req 14: WHEN the red step is outside the repository's control THEN the report says which and the builder stops.

## 5. Out of scope

- Coverage, code-quality or download-count badges (need an external account); Python, Node or Nix version badges.
- Badges in the guide, `site/` or docs pages; translating or restructuring the README.
- Changing workflows to improve a badge (for example a `push` trigger on `image.yml`). A workflow change is allowed
  only as the fix of a red step (Req 9, 13).
- Improving the gate beyond making it pass (new checks, speed, caching).

## 6. Conflicts with existing specs

None in `openspec/specs/` or `docs/adr/`: nothing there covers README content or the CI gate's step list. Constraints
followed: `AGENTS.md` rule 4 (100% coverage, never skip a failing test), rule 5 (`nix run .#quality` before pushing),
rule 8 (CI green to merge, no `--admin`), rule 9 (no attribution trailers, which wins over the harness suggestion),
rule 2 and ADR 0010 (Conventional Commits, `docs` type for the README, so no release is expected from it alone; not
run). ADR 0009 (testing strategy) forbids lowering the coverage gate as a fix.

## 7. Open questions

- **Which step is red, and what is its log?** I could not read it (no shell access in this session, no CI log in the
  request). The suspects in Req 11 and 12 are from reading `justfile`, `.prettierignore`, `commitlint.config.mjs`, not
  from a failure. If the cause is outside the files named here, the plan changes; this would change the design of the
  fix, not of the badges.
- Is `bhoudebert/lookout` public? If private, workflow, release and package badges render broken for anonymous
  visitors.
- Is a package published at `ghcr.io/bhoudebert/lookout`? If not, drop Req 5; nothing else depends on it.
- Does the owner want the exact `agent-motoride` set? It is unseen; a badge needing an external account would be a
  design change.
- `ci.yml` uses `actions/checkout@v7` and `actions/upload-artifact@v7`. I did not verify those versions exist; if the
  job fails at "Set up job", that is the cause (Req 14 if it is not fixable by pinning an existing version).
