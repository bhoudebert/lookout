# Design: GitHub badges on the README

## Approach

One edit to `README.md`: insert a single badge row between the `# Lookout` title (line 1) and the first paragraph
("A self-hosted watch tower…"), separated by blank lines. The five badges, their order, alt text and URLs are fixed by
`spec.md` requirement 3. This design adds nothing to that table; it only says how to write and check it.

Layout: all five badges on one line, separated by single spaces. Markdown renders them inline, and a single line keeps
R1 trivially checkable (the first non-empty line after the title starts with `[![CI status]`). The line is about 700
characters, which is acceptable for a README. Prettier or another formatter is not run on Markdown here, and no
hard-wrap rule applies to a line made only of links. If `just docs` or the format step rewraps it, the badges can be
put one per line with no blank line between them. They still render as one paragraph.

```
# Lookout

[![CI status](R/actions/workflows/ci.yml/badge.svg?branch=main)](R/actions/workflows/ci.yml) [![Latest release](…)](R/releases) [![MIT licence](…)](R/blob/main/LICENSE) [![Python 3.13+](…)](https://www.python.org/downloads/) [![Pages deploy](R/actions/workflows/pages.yml/badge.svg?branch=main)](https://bhoudebert.github.io/lookout/)

A self-hosted watch tower …
```

`R` is written out in full (`https://github.com/bhoudebert/lookout`) in the file. Exact URLs come from the spec table.

## Files touched

- `README.md`: the one inserted line plus a blank line.
- `docs/shelf/work-d68a9fbc73f9/*`: work documents only.

No code, workflow, test, spec, ADR, guide, site or ROADMAP change (spec requirements 8 and 9). No ADR: a README badge row
is not an architectural decision.

## Facts checked against the repository

- `ci.yml` runs on `push` to `main`, so `?branch=main` has runs to report.
- `pages.yml` runs on `push` to `main` and `workflow_dispatch`, so badge e has a `main` run once it fires.
- `LICENSE` exists at the repository root (R4c).
- `pyproject.toml` has `requires-python = ">=3.13"` and `license = "MIT"`, so badges c and d are true today.
- Workflow names are `CI` and `Pages`. The badge URLs use the file names, which is what GitHub keys on.
- `release.yml` publishes the image only on a release, which is why the Release badge stands in for the image (req 7).

## Data shapes and errors

Nothing runs, so there is no error handling in code. The failure modes are the spec's accepted edges: no release yet,
no `main` run of Pages yet, a private repository. Each degrades to the alt text or a "no status" image. The Python badge
is static and can drift; the guard is the merge-time check below, not automation, because adding a workflow is out of
scope.

## Verification

No tests exist for README content, and adding a test would break the "README only" rule (req 8) and coverage
expectations. Verification is a reviewer or shell check on the branch, to be run by the implementer and listed in the PR
under "what was verified":

1. `sed -n 1,5p README.md`: the row is line 3, the title is line 1, the paragraph follows (R1).
2. `grep -o '\[!\[[^]]*\]' README.md | head -5`: exactly the five alt texts, in order (R2, R3).
3. Each of the five image URLs and link URLs is `grep -F`'d from the spec table. Hosts are only `img.shields.io` and
   `github.com` (R2).
4. `grep -c 'style=flat' ` on the row gives 3 (badges b, c, d) (R5).
5. `grep -ni 'codecov\|coveralls\|ghcr' README.md` hits nothing in the badge row (R6).
6. `grep '^requires-python' pyproject.toml` returns `>=3.13` (R4d).
7. `git diff --name-only main...HEAD` lists only `README.md` and `docs/shelf/work-d68a9fbc73f9/*` (R7).

What cannot be verified before merge: how the badges render, because the workflow badges depend on a public
repository and on runs that happen on `main`. Say so in the PR. Commit: `docs(readme): add status badges`, within the
100-character limit and kebab-case scope. No attribution trailers (AGENTS.md rule 9) apart from what the harness
mandates.

## Alternatives rejected

- **Generate the Python badge from `pyproject.toml`** (shields `pypi/pyversions` or `python-version-from-toml`): the
  package is not on PyPI, and the TOML endpoint needs a shields-side fetch of the file. A static badge with a merge
  check is simpler, as the spec decided.
- **A table or a centred HTML `<p align="center">` block**: more markup, not what the spec asks for, harder to grep.
- **Badge for Image, coverage or Codecov**: ruled out by the spec (reqs 6 and 7).
- **A CI check that the README badges match `pyproject.toml`**: it would touch workflows and tests, which the spec
  forbids, and is out of proportion to one static line.

## Conflicts with existing specifications or ADRs

None. No file in `openspec/specs/` or `docs/adr/` covers the README. AGENTS.md rule 6 (README with the change) is
satisfied, since the README is the change.
