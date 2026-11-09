# Plan: GitHub badges on the README

Source: `spec.md` (requirements 1-9, scenarios R1-R7) and `design.md`. One edit to `README.md`; nothing runs, so the
"tests" are the shell checks listed in `design.md` (Verification). Test first means: run the check, see it fail on the
current README, then make the edit, see it pass. `R` = `https://github.com/bhoudebert/lookout`.

No conflict with any spec or ADR (see `spec.md` section 5 and `design.md`). No file under `openspec/specs/` or
`docs/adr/` changes; `ROADMAP.md` only if an item for this work already exists (step 3).

Risk: the riskiest part is not the edit but the premises (public repository, `requires-python`, workflow file names, the
`LICENSE` file). Step 1 checks them first, so a false premise stops the work before any edit.

## Step 1. Check the premises (riskiest, no file touched)

Test (all must pass before step 2; if one fails, stop and report to the user):

- `grep '^requires-python' pyproject.toml` returns `>=3.13` (R4d, req 5).
- `LICENSE` exists at the repository root (R4c).
- `.github/workflows/ci.yml` and `.github/workflows/pages.yml` exist, and both trigger on `push` to `main`.
- `docs/guide/.vitepress/config.mts` still has `base: "/lookout/guide/"`, so `https://bhoudebert.github.io/lookout/` holds.
- `gh repo view bhoudebert/lookout --json visibility` says `PUBLIC`, if `gh` is reachable. If it is not reachable, say so
  in the PR; the spec decided "public".
- `grep -n 'Lookout' ROADMAP.md`-style scan for a badge or README item; note the result for step 3.

Files: none.

## Step 2. Write the failing check, then add the badge row

Test first: save the checks of `design.md` items 1-7 as a throwaway shell snippet (kept in `$TMPDIR`, not committed, since
req 8 forbids other files). Run it on the unchanged README: items 1-5 must fail.

Then edit `README.md`: after line 1 (`# Lookout`), add a blank line, one line with the five badges separated by single
spaces, and a blank line before "A self-hosted watch tower". Exact content, in this order:

1. `[![CI status](R/actions/workflows/ci.yml/badge.svg?branch=main)](R/actions/workflows/ci.yml)`
2. `[![Latest release](https://img.shields.io/github/v/release/bhoudebert/lookout?style=flat)](R/releases)`
3. `[![MIT licence](https://img.shields.io/github/license/bhoudebert/lookout?style=flat)](R/blob/main/LICENSE)`
4. `[![Python 3.13+](https://img.shields.io/badge/python-3.13%2B-blue?style=flat)](https://www.python.org/downloads/)`
5. `[![Pages deploy](R/actions/workflows/pages.yml/badge.svg?branch=main)](https://bhoudebert.github.io/lookout/)`

with `R` written out in full. Do not touch any other line.

Files: `README.md`.

Test that proves it (the snippet from above now passes entirely):

- `sed -n 1,5p README.md`: title line 1, row line 3, paragraph after (R1).
- `grep -o '\[!\[[^]]*\]' README.md | head -5`: the five alt texts in order (R2, R3).
- each image URL and link URL `grep -F`'d from the table; only hosts `img.shields.io` and `github.com` (R2).
- `style=flat` appears 3 times on the row (R5).
- `grep -ni 'codecov\|coveralls\|ghcr' README.md` has no hit in the badge row (R6).
- If the format step rewraps the row, put one badge per line with no blank line between them (design fallback), and
  rerun the checks adjusted to that layout.

## Step 3. Confirm scope, then the gate

Test:

- `git diff --name-only main...HEAD` lists only `README.md` and `docs/shelf/work-d68a9fbc73f9/*` (R7, req 8).
- `ROADMAP.md`: if step 1 found an item for badges, mark it done in this PR (req 9); otherwise leave it.
- Run `nix run .#quality` (or `just quality`) if the environment allows it; a README-only change should pass untouched.
  If it cannot run here (sandbox, no nix), say so in the PR instead of claiming it passed.

Files: none beyond the above (`ROADMAP.md` only in the case named).

## Step 4. Commit and pull request

- Branch: `docs/readme-badges` (never commit to `main`, AGENTS.md rule 1). Commit:
  `docs(readme): add status badges`, one concern, header under 100 characters.
- Pull request from the template: summary; spec touched: none (README only, no behaviour change); verified: the checks
  of step 2 and 3; not verified: how the badges render, because workflow badges depend on a public repository and on
  runs on `main`, and the Release badge shows "no releases" until the first release (spec edges R4b, R4e).
- Attribution lines: AGENTS.md rule 9 says no trailers or generated-by footers; the harness for this session asks for
  some. This is a conflict between the two instructions; the implementer follows the repository rule unless the user says
  otherwise, and mentions it in the hand-off.
- CI must be green before merge; never merge red, never `--admin` (rule 8).

Files: none new.

## Out of scope (do not do)

Coverage or Codecov badge, Image/ghcr badge, `image.yml` badge, any workflow, site, guide, test or spec change, or any
restructuring of the README (spec section 4).
