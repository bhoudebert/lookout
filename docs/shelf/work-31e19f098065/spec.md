Round 0 feedback was "Go it is done" (an approval, no change requested); this is the first spec, written from the repository.

# Spec: status badges on the main README

## 1. Goal

Je veux voir, en haut du `README.md` principal, une rangée de badges qui donne l'état du projet d'un coup d'œil : CI, CodeQL, dernière version publiée, versions des technologies utilisées (Python, Node), et conformité aux Conventional Commits.

Repository facts the spec relies on: repo is `bhoudebert/lookout`; workflows `CI` (`ci.yml`), `Release` (`release.yml`, release-please), `Pages`, `Image`, `PR title`; Python `>=3.13` (`pyproject.toml`); Node `24` (`.nvmrc`); Conventional Commits enforced (ADR 0010, `commitlint.config.mjs`); licence MIT; no CodeQL workflow exists; no release exists yet (manifest at `0.0.0`); README has no badges today.

## 2. Requirements

1. The README SHALL show a badge row directly under the `# Lookout` title (before the tagline), as Markdown only, with no other README text changed.
2. The row SHALL contain a CI badge showing the status of the `ci.yml` workflow on `main`, linking to that workflow's runs page.
3. The row SHALL contain a CodeQL badge showing the status of a CodeQL workflow on `main`, linking to its runs page.
4. A CodeQL workflow SHALL exist in `.github/workflows/` (analysing at least Python and JavaScript/TypeScript, on push to `main`, on pull requests, and on a weekly schedule) so that requirement 3 is not a dead badge.
5. The row SHALL contain a release badge showing the latest GitHub release/tag, linking to the releases page.
6. The row SHALL contain a Python badge and a Node.js badge whose version is read from the repo (`requires-python` in `pyproject.toml`, `.nvmrc`), not typed by hand, so they cannot drift.
7. The row SHALL contain a Conventional Commits badge (version 1.0.0) linking to conventionalcommits.org.
8. The row SHALL contain a licence badge (MIT), linking to `LICENSE`.
9. Every badge SHALL have non-empty alt text and a link target, and every badge URL SHALL point to `bhoudebert/lookout`.
10. The row SHALL render on one or two lines on GitHub at desktop width and SHALL NOT use more than 8 badges.

## 3. Scenarios

1. (R1) WHEN the README is opened on GitHub THEN the badges appear between the title and the tagline, and the rest of the file is byte-identical to before.
2. (R2) WHEN the latest `CI` run on `main` passes THEN the badge reads "passing"; WHEN it fails THEN it reads "failing". Edge: WHEN the workflow file is renamed THEN the badge breaks, so the badge URL names `ci.yml` exactly.
3. (R3) WHEN the CodeQL workflow has run on `main` THEN the badge shows its status. Edge: WHEN it has never run (just merged) THEN the badge shows "no status" until the first run; this is accepted.
4. (R4) WHEN a PR is opened THEN CodeQL runs on it; WHEN a week passes without pushes THEN the scheduled run still fires. Edge: the workflow only requests the permissions CodeQL needs (`security-events: write`, `contents: read`).
5. (R5) WHEN a GitHub release exists THEN the badge shows its tag. Edge: WHEN no release exists (today, manifest `0.0.0`) THEN the badge shows "no releases" rather than a wrong number; it fills in on the first release-please release.
6. (R6) WHEN `.nvmrc` changes from 24 to 26 THEN the Node badge shows 26 with no README edit. WHEN `requires-python` changes THEN the Python badge follows. Edge: if the dynamic source is unreachable the badge shows an error state rather than a stale number.
7. (R7) WHEN a reader clicks the Conventional Commits badge THEN they land on conventionalcommits.org/en/v1.0.0/.
8. (R8) WHEN a reader clicks the licence badge THEN they land on the `LICENSE` file.
9. (R9) WHEN badge URLs are searched for the owner/repo THEN every one contains `bhoudebert/lookout` (no copy-paste from another project).
10. (R10) WHEN the README is viewed at 1280 px width THEN the row wraps to at most two lines.

## 4. Out of scope

- Coverage, downloads, stars, Docker image size or Pages-deploy badges.
- Changing existing workflows (CI, Release), release-please configuration or commit rules.
- Badges in the VitePress guide or other docs.
- Fixing the `0.0.0` version or cutting a first release.
- Automated tests of badge rendering (checked by eye on GitHub, plus a link check if CI already has one).

## 5. Open questions

1. **CodeQL does not exist yet.** I assume adding a minimal CodeQL workflow (R4) is wanted, as the request lists CodeQL as a badge. If you would rather use GitHub's "default setup" (configured in repo settings, no workflow file), there is no workflow to badge and R3/R4 change to a Security-tab link. This changes the design; please confirm.
2. **Dynamic version badges** (R6) rely on a third-party service (shields.io) reading raw files from the default branch. If the repo is private, those badges will not render. Is the repo public? If not, the fallback is static badges (`python 3.13+`, `node 24`), which can drift.
3. Is the Rust/Java mention in the request only an example? I found none in the repo (Python backend, React frontend, Nix, Docker), so I left them out. Should a Nix or Docker badge be added?
