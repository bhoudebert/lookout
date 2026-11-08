Round 0 feedback was "as simple as possible, drop what is too complex": the CodeQL workflow and the auto-synced version badges are dropped; what remains is six plain badges in the README, nothing else.

# Spec: status badges on the main README

## 1. Goal

Je veux voir, en haut du `README.md` principal, une rangée de badges simples : CI, dernière version publiée, versions Python et Node, Conventional Commits, licence. Rien d'autre ne change.

Repository facts: repo `bhoudebert/lookout`; workflow `ci.yml` (name `CI`); Python `>=3.13` (`pyproject.toml`); Node `24` (`.nvmrc`); Conventional Commits enforced (`commitlint.config.mjs`); licence MIT; README has no badges; no CodeQL workflow exists; no release yet (manifest `0.0.0`).

## 2. Requirements

1. The README SHALL show a badge row directly under the `# Lookout` title, before the tagline; no other line of the README changes.
2. The row SHALL contain a CI badge for the `ci.yml` workflow on `main`, linking to that workflow's runs page.
3. The row SHALL contain a release badge showing the latest GitHub release, linking to the releases page.
4. The row SHALL contain a Python badge (`3.13+`) and a Node.js badge (`24`), as static badges.
5. The row SHALL contain a Conventional Commits 1.0.0 badge linking to conventionalcommits.org.
6. The row SHALL contain an MIT licence badge linking to `LICENSE`.
7. Every badge SHALL have non-empty alt text and a link, and every GitHub-derived badge URL SHALL name `bhoudebert/lookout`.
8. The change SHALL touch only `README.md` (no new workflow, no config change).

## 3. Scenarios

1. (R1) WHEN the README is opened THEN the badges sit between the title and tagline. Edge: the diff shows only added badge lines.
2. (R2) WHEN the latest `CI` run on `main` passes THEN the badge reads "passing"; WHEN it fails THEN "failing". Edge: WHEN `ci.yml` is renamed THEN the badge breaks; accepted.
3. (R3) WHEN a release exists THEN its tag shows. Edge: WHEN none exists (today) THEN the badge shows "no releases" until the first release-please release.
4. (R4) WHEN a reader views the row THEN they see "python 3.13+" and "node 24". Edge: these are typed by hand and can drift if `pyproject.toml` or `.nvmrc` change; accepted for simplicity.
5. (R5) WHEN the badge is clicked THEN conventionalcommits.org/en/v1.0.0/ opens.
6. (R6) WHEN the badge is clicked THEN the `LICENSE` file opens.
7. (R7) WHEN badge URLs are searched THEN each GitHub-derived one contains `bhoudebert/lookout`.
8. (R8) WHEN the change is reviewed THEN `git diff --stat` lists only `README.md`.

## 4. Out of scope

- CodeQL badge and workflow (needs a new workflow file; see open question 1).
- Badges that read versions from the repo automatically.
- Coverage, downloads, stars, Docker, Pages badges.
- Any change to workflows, release-please, or commit rules; cutting a first release.
- Rust/Java badges (none in the repo).

## 5. Open questions

1. **CodeQL.** Dropped as too complex. If wanted, it is a small follow-up: either add a CodeQL workflow (then badge it) or enable GitHub "default setup" in repo settings (no badge possible). Which one, if any? This changes the design.
2. Is the repo public? The badges (GitHub Actions and release status) only render for anonymous readers on a public repo.
