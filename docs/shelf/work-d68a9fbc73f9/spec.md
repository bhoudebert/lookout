# Spec: GitHub badges on the README

Round 1 changes: English only; the Pages link is pinned to a confirmed URL; the Image badge is dropped (no checkable
badge exists for it); style pinned to `flat`; exact alt text and URLs listed; open questions turned into decisions;
a merge-time check for the Python badge; scope wording fixed.

## 1. Goal

I want a row of GitHub badges at the top of Lookout's `README.md`, right under the title, in the way
`bhoudebert/agent-motoride` does it, so the state of the project (CI, release, licence, Python version, website) is
visible at a glance. "Do as much as possible, with less or more" is read as: show every badge that is true and
checkable for this repository, and no more.

## 2. Requirements

The list in requirement 4 is authoritative. The reference repository could not be opened, so matching it is not a
requirement.

1. The `README.md` SHALL show one badge row directly under the `# Lookout` title and above the first paragraph.
2. Each badge SHALL be a Markdown image wrapped in a link: `[![alt](image-url)](link-url)`.
3. The row SHALL contain exactly these five badges, in this order, with exactly this alt text, image URL and link URL
   (`R` = `https://github.com/bhoudebert/lookout`):

   - a. alt `CI status`, image `R/actions/workflows/ci.yml/badge.svg?branch=main`, link `R/actions/workflows/ci.yml`
   - b. alt `Latest release`, image `https://img.shields.io/github/v/release/bhoudebert/lookout?style=flat`, link
     `R/releases`
   - c. alt `MIT licence`, image `https://img.shields.io/github/license/bhoudebert/lookout?style=flat`, link
     `R/blob/main/LICENSE`
   - d. alt `Python 3.13+`, image `https://img.shields.io/badge/python-3.13%2B-blue?style=flat`, link
     `https://www.python.org/downloads/`
   - e. alt `Pages deploy`, image `R/actions/workflows/pages.yml/badge.svg?branch=main`, link
     `https://bhoudebert.github.io/lookout/`

4. Badges b, c and d SHALL carry `style=flat`. Badges a and e use GitHub's own workflow badge, which has no style
   parameter and is `flat`-looking; this is accepted and is the only exception to uniformity.
5. The Python badge text (`3.13+`) SHALL match `requires-python` in `pyproject.toml` (`>=3.13`) at merge time.
6. The README SHALL NOT show a coverage badge or any third-party service badge other than `img.shields.io`
   (coverage is a gate in `nix run .#quality`, not a reported number).
7. The README SHALL NOT show an Image (ghcr) badge: shields.io has no ghcr endpoint, `release.yml` only publishes when a
   release is created, and the package link would 404 before the first release. The Release badge (b) stands for it.
8. The pull request SHALL change only `README.md` and files under `docs/shelf/work-d68a9fbc73f9/`. No code, workflow
   or test change.
9. No behaviour changes, so no file under `openspec/specs/` is added or changed (AGENTS.md rule 3). `ROADMAP.md` is
   updated only if an item for this work exists there.

Decisions that were open questions:

- Repository visibility: the repository is treated as public (the website and `ghcr.io/bhoudebert/lookout` are
  published for users). Default if wrong: workflow badges show "not found" and the owner must make the repository public.
- Python badge: static, with the merge-time check of requirement 5.
- Pages badge: it shows the status of the last `pages.yml` run, not whether the site is up. Its link target
  `https://bhoudebert.github.io/lookout/` is confirmed by `base: "/lookout/guide/"` and the "Website" link in
  `docs/guide/.vitepress/config.mts`.

## 3. Scenarios

- R1 WHEN the README is read THEN the badge row is after line 1 (`# Lookout`) and before "A self-hosted watch tower".
  Check: the first non-empty line after the title contains `[![CI status]`.
- R2 WHEN the row is parsed THEN it holds exactly five `[![alt](img)](link)` items matching the table in requirement 3,
  and every image host is `img.shields.io` or `github.com`. Check: grep the README for each alt text and URL.
- R3 WHEN images fail to load THEN each alt text from the table is still shown.
- R4a WHEN the latest `ci.yml` run on `main` fails THEN badge a shows failing; a pull request branch does not change it
  (`?branch=main`).
- R4b WHEN no release exists yet THEN badge b shows "no releases" and still links to `R/releases` (edge; accepted).
- R4c WHEN the clicked licence badge opens THEN `LICENSE` exists at the repository root and resolves.
- R4d WHEN `requires-python` in `pyproject.toml` is not `>=3.13` THEN the merge check fails until the badge text is
  edited (edge: the badge cannot follow by itself).
- R4e WHEN `pages.yml` has not run on `main` yet, or the repository is private THEN badge e shows "no status" or
  "not found" and the link may 404 (edge; accepted, see decisions).
- R5 WHEN badges b, c, d are read THEN each URL contains `style=flat`.
- R6 WHEN a reviewer looks for a coverage or ghcr badge THEN there is none.
- R7 WHEN the pull request diff is read THEN only `README.md` and `docs/shelf/work-d68a9fbc73f9/*` changed.

## 4. Out of scope

- A coverage badge or any third-party service (Codecov, Coveralls): needs an account and a workflow change.
- An Image/ghcr badge, and a badge for `image.yml` (it only runs on pull requests, so a `main` badge says nothing).
- Changing workflows, the website (`site/`), the guide, or the ROADMAP.
- Dashboard, LLM or source badges: they are not status signals.
- Restructuring the rest of the README.

## 5. Conflicts with existing specs

None. No file under `openspec/specs/` describes the README. `AGENTS.md` rule 6 (README with the change when the
overview changes) is not contradicted; rule 9 (no attribution) is respected, since badges are plain status links. ADR
0010 (release-please) is what makes the Release badge move; it is not changed. No ADR is touched.

## 6. Open questions

1. `bhoudebert/agent-motoride` could not be opened. If its row differs, the list in requirement 3 is still the one
   built; say so if you want a badge added or removed. This changes the table, not the design.
2. Is the repository really public? Decided as public (see decisions); a "no" makes badges a, e and the links dead
   and would change whether the row is worth adding at all.
