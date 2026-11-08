# Spec: GitHub badges on the README

## 1. Goal

Je veux une rangée de badges GitHub en haut du `README.md` de Lookout, juste sous le titre, comme sur
`bhoudebert/agent-motoride`, pour qu'on voie en un coup d'œil l'état du projet (CI, version, licence, etc.). « Do as
much as possible, with less or more » is read as: show the badges that are true and useful for this repository, and
no more.

## 2. Requirements

1. The `README.md` SHALL show a badge row directly under the `# Lookout` title and above the first paragraph.
2. Each badge SHALL be a Markdown image wrapped in a link to the page it describes.
3. Each badge SHALL carry non-empty alt text that names what it shows (for example "CI status").
4. The row SHALL contain these badges, and each SHALL point at `bhoudebert/lookout`:
   a. CI: the `ci.yml` workflow status on `main`, linking to its runs.
   b. Release: the latest GitHub release, linking to the releases page.
   c. Licence: MIT, linking to `LICENSE`.
   d. Python: 3.13 or newer, matching `requires-python` in `pyproject.toml`.
   e. Image: the container published to `ghcr.io/bhoudebert/lookout` by `release.yml`, linking to the package page.
   f. Pages: the `pages.yml` workflow status, linking to the published website.
5. Every badge SHALL use the same style (`shields.io`, one `style` value) so the row looks uniform.
6. The README SHALL NOT show a badge for something this repository does not do (no coverage-service badge: coverage is
   a gate in `nix run .#quality`, not a reported number).
7. The change SHALL touch `README.md` only, plus this spec. No code, workflow, or test changes.

## 3. Scenarios

- R1 WHEN the README is opened on GitHub THEN the badges appear after the title and before "A self-hosted watch tower".
- R2 WHEN a badge is clicked THEN it opens the matching page (workflow runs, releases, LICENSE, package, website).
- R3 WHEN images fail to load (offline, blocked shields.io) THEN the alt text still says what each badge was.
- R4a WHEN the latest `ci.yml` run on `main` fails THEN the CI badge shows failing (edge: the badge is bound to `main`,
  not to a pull request branch).
- R4b WHEN no release exists yet THEN the release badge shows "no releases" rather than breaking (edge case; accepted).
- R4d WHEN `requires-python` changes THEN the Python badge is out of date until edited by hand (edge; see open question 2).
- R5 WHEN the row is viewed THEN all badges have equal height and one visual style.
- R6 WHEN a reviewer looks for a coverage badge THEN there is none.
- R7 WHEN the pull request diff is read THEN only `README.md` and the `docs/shelf/` documents changed.

## 4. Out of scope

- A coverage badge or any third-party service (Codecov, Coveralls): needs an account and a workflow change.
- Changing workflows, the website (`site/`), the guide, or the ROADMAP.
- Badges for the dashboard, LLM, or sources: they are not status signals.
- Translating or restructuring the rest of the README.

## 5. Conflicts with existing specs

None. No file under `openspec/specs/` describes the README, and `AGENTS.md` rule 6 asks for README changes only "when
the overview changes", which a badge row does not contradict. No ADR is touched. Rule 9 (no attribution footers) is
respected: badges are plain links, not generated-by marks. The one badge using the `release.yml` image tag path
(R4e) depends on ADR 0010 (release-please) continuing to publish to `ghcr.io/${{ github.repository }}`.

## 6. Open questions

1. I could not open `bhoudebert/agent-motoride`, so the badge set and style are my inference from this repository's
   workflows. If its row differs (for example flat-square, or a badge I did not list), tell me; this would change the
   badge list, not the design.
2. Should the Python badge be static (simple, can drift) or read from `pyproject.toml` through a dynamic shields
   endpoint (always true, but an extra moving part)? Default: static.
3. Is the repository public and are `ghcr.io` packages public? If the package is private, the Image badge (4e) shows
   nothing useful and should be dropped.
4. Is the Pages site live on GitHub Pages? If not, drop badge 4f.
