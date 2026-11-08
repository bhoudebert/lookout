# Spec: GitHub badges on the README

## 1. Goal

Je voudrais une rangée de badges GitHub en haut du `README.md`, juste sous le titre, comme sur
`bhoudebert/agent-motoride`, pour voir d'un coup d'œil l'état du projet (CI, release, licence, image, docs). Tout ce qui
est possible avec l'existant, sans rien inventer d'autre.

(I could not read the reference repo from here; the set below is the usual one for a repo with these workflows.)

## 2. Requirements

1. The README SHALL show a badge block directly after the `# Lookout` title and before the description paragraph.
2. The block SHALL contain one status badge per existing workflow that reports a meaningful state on `main`: CI
   (`ci.yml`), Release (`release.yml`), Image (`image.yml`), Pages (`pages.yml`). `pr-title.yml` SHALL NOT get a badge
   (it only runs on pull requests, so it has no `main` state).
3. The block SHALL contain a licence badge (MIT, matching the `LICENSE` file and the README's "MIT licence" line).
4. The block SHALL contain a latest-release badge, linking to the GitHub releases page.
5. Every badge SHALL be a Markdown image wrapped in a link to the thing it reports (the workflow runs page, the
   `LICENSE` file, the releases page), and SHALL have non-empty alt text.
6. Every badge URL SHALL target `bhoudebert/lookout` (the repository's actual remote) and, for workflow badges, the
   `main` branch.
7. Badges SHALL be served by GitHub (`github.com/.../badge.svg`) or shields.io only; no other service, no account,
   no token, no new secret.
8. The change SHALL touch only `README.md` (plus this work's documents). No code, workflow, or config file changes.
9. The rest of the README SHALL be unchanged.

## 3. Scenarios

- Req 1: WHEN the README is opened THEN line 1 is `# Lookout`, the badge block follows, and the line "A self-hosted
  watch tower..." comes after it. Edge: a blank line separates the block from the paragraph so GitHub renders it as
  its own block.
- Req 2: WHEN a workflow file is listed in `.github/workflows/` and runs on `main` THEN a badge naming it exists.
  Edge: `pr-title.yml` has no badge.
- Req 2 (name match): WHEN a badge uses the workflow file name THEN that file exists (a rename would break the
  badge; the check is a grep of each badge's `<file>.yml` against the directory).
- Req 3: WHEN the licence badge is clicked THEN it opens `LICENSE`. Edge: the text says MIT, as `LICENSE` does.
- Req 4: WHEN no release exists yet THEN shields shows "no releases"; this is acceptable and not an error.
- Req 5: WHEN images fail to load THEN the alt text still names each badge.
- Req 6: WHEN every URL is inspected THEN none contains another owner or repo name, such as `agent-motoride`.
- Req 7: WHEN the URLs are listed THEN every host is `github.com` or `img.shields.io`.
- Req 8: WHEN the diff is read THEN only `README.md` changed outside `docs/shelf/`.

## 4. Out of scope

- Coverage, code-quality, or download-count badges (no coverage service is configured; adding one needs an account).
- Python, Node, or Nix version badges.
- Editing the guide, the website in `site/`, or the docs pages to carry badges.
- Changing workflows to make a badge look better (e.g. adding a push trigger).
- Translating or restructuring the README.

## 5. Conflicts with existing specs

None. No file in `openspec/specs/` or `docs/adr/` covers README content. `AGENTS.md` asks to update the README when the
overview changes; this is a presentational change, and `CONTRIBUTING.md` classes README edits as type `docs` (no
release). The commit should therefore be `docs: add status badges to the README` (ADR 0010).

## 6. Open questions

- Is `bhoudebert/lookout` the public slug? It is the remote, but if the repo is private the workflow and release
  badges render as broken or "not found" for anonymous visitors. This does not change the design.
- Should the Image badge be dropped if `image.yml` only builds without publishing? It has no `main` publish proof
  from what I read. Default here: keep it, since it runs on `main`.
- Do you want the exact set from `agent-motoride`? Not visible to me. If it includes a badge this spec excludes, say
  which and I will add it, unless it needs an external account (then it is a design change).
