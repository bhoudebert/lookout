# Spec: GitHub badges on the README

Round 2 changes: Image badge dropped (`image.yml` never runs on `main`); badge set listed exactly (CI, Pages, Release, licence, latest release, container link); Release kept with its reason stated; Req 6 and licence checks made mechanical; link targets fixed; goal in English; commit rule softened.

## 1. Goal

I want a row of GitHub badges at the top of `README.md`, right under the title, like on `bhoudebert/agent-motoride`, so
the state of the project is visible at a glance (CI, docs site, release, licence, container image). As much as the
existing repository allows, without inventing anything else.

(I could not read the reference repo from here; the set below is the usual one for a repo with these workflows.)

## 2. Requirements

1. The README SHALL show a badge block directly after the `# Lookout` title and before the description paragraph.
2. The block SHALL contain exactly these workflow-status badges, each using `branch=main`, and no other workflow badge:
   - CI: `ci.yml` (runs on push to `main`);
   - Pages: `pages.yml` (runs on push to `main`);
   - Release: `release.yml`, kept because it runs on every push to `main` and so shows whether release-please is
     healthy. It says little about the product itself; it is not a quality signal.

   `image.yml` SHALL NOT get a badge: it runs only on `pull_request` and `workflow_dispatch`, so `main` usually has no
   run and the badge would read "no status". `pr-title.yml` SHALL NOT get a badge either (pull requests only).
3. The block SHALL contain a licence badge (MIT) linking to `LICENSE` (`https://github.com/bhoudebert/lookout/blob/main/LICENSE`).
   `LICENSE` SHALL be MIT text (it is, today: it names MIT), and the badge text SHALL say MIT.
4. The block SHALL contain a latest-release badge (shields `github/v/release/bhoudebert/lookout`) linking to
   `https://github.com/bhoudebert/lookout/releases`.
5. The block SHALL contain a container badge that points at the published image, not at a workflow: a shields badge
   linking to `https://github.com/bhoudebert/lookout/pkgs/container/lookout` (the `ghcr.io/bhoudebert/lookout` package page).
   Its label SHALL be static text (for example "ghcr.io"), so it never depends on a run.
6. Every badge SHALL be a Markdown image wrapped in a link, with non-empty alt text. Link targets: CI → its workflow
   page `https://github.com/bhoudebert/lookout/actions/workflows/ci.yml`; Pages → the published site
   `https://bhoudebert.github.io/lookout/`; Release → `.../actions/workflows/release.yml`; licence, release and container
   as in Req 3 to 5.
7. Every `github.com` or `img.shields.io` path in the block SHALL begin with `bhoudebert/lookout` (after the
   `github.com/` host, or after `img.shields.io/github/<kind>/` for shields). The one exception is the Pages link on
   `bhoudebert.github.io/lookout/`.
8. Badges SHALL be served by GitHub (`github.com/.../badge.svg`) or shields.io only; no other service, account, token
   or secret.
9. The change SHALL touch only `README.md` (plus this work's documents). No code, workflow or config file changes.
10. The rest of the README SHALL be unchanged.

## 3. Scenarios

- Req 1: WHEN the README is opened THEN line 1 is `# Lookout`, the badge block follows, and "A self-hosted watch
  tower..." comes after it. Edge: a blank line separates the block from the paragraph.
- Req 2: WHEN the workflow badges are listed THEN they are exactly `ci.yml`, `pages.yml`, `release.yml`, each with
  `branch=main`. Edge: no `image.yml` and no `pr-title.yml` badge.
- Req 2 (name match): WHEN each badge's `<file>.yml` is grepped against `.github/workflows/` THEN the file exists
  (a rename would break the badge).
- Req 3: WHEN the licence badge is clicked THEN it opens `blob/main/LICENSE`. Edge: `grep -c MIT LICENSE` is above 0
  and the badge says MIT.
- Req 4: WHEN no release exists yet THEN shields shows "no releases"; acceptable, not an error.
- Req 5: WHEN the container badge is clicked THEN it opens the `lookout` package page. Edge: if the package is not yet
  published the page 404s; the badge still renders because its label is static.
- Req 6: WHEN images fail to load THEN the alt text still names each badge. Edge: the Pages badge opens the site, not a
  runs page.
- Req 7: WHEN every URL is listed THEN each GitHub or shields path starts with `bhoudebert/lookout`, and none contains
  `agent-motoride` or another owner.
- Req 8: WHEN hosts are listed THEN each is `github.com`, `img.shields.io` or `bhoudebert.github.io`.
- Req 9: WHEN the diff is read THEN only `README.md` changed outside `docs/shelf/`.
- Req 10: WHEN the diff is read THEN no README line below the badge block changed.

## 4. Out of scope

- Coverage, code-quality or download-count badges (no service configured; would need an account).
- Python, Node or Nix version badges.
- Badges in the guide, `site/` or docs pages.
- Changing workflows to improve a badge (for example adding a `push` trigger to `image.yml`).
- Translating or restructuring the README.

## 5. Conflicts with existing specs

None. No file in `openspec/specs/` or `docs/adr/` covers README content. `AGENTS.md` asks to update the README when the
overview changes; this is presentational. Commit type is `docs:` (ADR 0010), e.g. `docs: add status badges to the
README`. In `release-please-config.json`, `docs` is a visible changelog section; release-please's default versioning
bumps only on `feat`/`fix`, so I expect no release from it alone, but I have not run it.

## 6. Open questions

- Is `bhoudebert/lookout` public? If private, workflow, release and package badges render broken for anonymous visitors.
  This does not change the design.
- Is the image actually published to `ghcr.io/bhoudebert/lookout`? The `image.yml` comment says publishing happens on
  release, but I did not confirm a package exists. If not, drop Req 5; no other requirement depends on it.
- Do you want the exact set from `agent-motoride`? Not visible to me. A badge needing an external account would be a
  design change.
