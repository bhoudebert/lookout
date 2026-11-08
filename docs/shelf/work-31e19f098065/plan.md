# Plan: status badges on the main README

Source: `spec.md` and `design.md` in this folder. The change is small. Only `README.md` is touched, and the "test first" is a
small check script run from the shell, not committed (R8 forbids touching any other file).

README today: line 1 `# Lookout`, line 2 blank, line 3 the tagline. No badges.

## Risk

The riskiest part is not the code. It is two things outside the repo, covered by steps 1 and 5:

- Whether the repo is public (spec open question 2). Without that, the dynamic badges cannot render for anonymous readers.
- Whether Prettier leaves the long badge lines alone.

## Steps

### Step 1. Check the facts the badges copy (no file changes)

- Touches: nothing, read-only.
- Do:
  - `.nvmrc` is `24`.
  - `pyproject.toml` has `requires-python = ">=3.13"`.
  - `.github/workflows/ci.yml` exists and its `name:` is `CI`.
  - `LICENSE` exists and is MIT.
  - `git remote -v` names `bhoudebert/lookout`.
  - `gh repo view bhoudebert/lookout --json visibility`, if `gh` is available, answers open question 2.
- Proof: all five values match `design.md`. If one differs, update the matching badge in step 3 and tell the owner.
- If the repo is private: stop and ask the owner. The design says to drop or replace the dynamic badges (CI and release).

### Step 2. Write the check first (it must fail)

- Touches: a scratch script in `$TMPDIR` (for example `$TMPDIR/check-badges.sh`), not committed.
- The script asserts, against `README.md`:
  1. Line 1 is `# Lookout`, lines 2 and 4+ are blank, line 3 is badge line 1, and the tagline is the first non-badge line (R1).
  2. There are exactly 6 lines matching `^\[!\[[^]]+\]\(https://img\.shields\.io/[^)]+\)\]\([^)]+\)$` (R7: non-empty alt, link present).
  3. The badge text contains each of these (R2 to R6):
     - `actions/workflow/status/bhoudebert/lookout/ci.yml?branch=main`
     - `github/v/release/bhoudebert/lookout`
     - `python-3.13%2B`
     - `node-24`
     - `Conventional%20Commits-1.0.0`
     - `licence-MIT`
     - the link targets `…/actions/workflows/ci.yml`, `…/releases`, `conventionalcommits.org/en/v1.0.0/`, and `(LICENSE)`.
  4. Every `img.shields.io/github/...` URL contains `bhoudebert/lookout` (R7).
  5. `git diff --numstat -- .` shows only `README.md`, with 0 deleted lines (R8).
- Proof: run it now. It fails on checks 1 to 3, because there are no badges yet. This shows the check can fail.

### Step 3. Add the badge row

- Touches: `README.md`. Insert after line 1: a blank line, then the six lines from the `design.md` table, in that order, one per line with no blank lines between them.
  The tagline and everything below stay unchanged. A blank line separates the row from the tagline.
- Proof: re-run the script from step 2. All checks pass, including that `git diff --numstat` shows added lines only.

### Step 4. Run the formatter and the quality gate

- Touches: `README.md` only if Prettier asks for a change.
- Do:
  - `npx prettier --check README.md`. If it fails, check that the failure comes from the new lines and not from lines that were already unformatted.
    If it comes from the new lines, run `--write` and re-run the step 2 script. If it comes from old lines, do not reformat them, because R1 says no other line changes.
    Report it instead.
  - `nix run .#quality`, if Nix is available.
- Proof: Prettier reports no problem for the added lines, and `git diff --stat` still lists only `README.md`.

### Step 5. Visual check after the push

- Touches: nothing.
- Do, after the change is on `main`: open the README on GitHub and confirm the six badges render in one row.
  - Release shows "no releases". That is expected until release-please cuts a release (manifest `0.0.0`).
  - CI shows passing or failing, according to the latest run.
  - The other four resolve.
- Proof: a screenshot or a short note in the PR description.
- Commit message: `docs: add status badges to the README` (Conventional Commits, enforced by `commitlint.config.mjs`).

## Not in this plan

CodeQL (workflow or badge), badges that read versions from the repo, coverage, downloads, Docker and Pages badges.
They are all out of scope in the spec.
