# Design: status badges on the main README

## Approach

Insert one badge row into `README.md`, directly under `# Lookout` (line 1) and before the tagline (line 3), separated by blank lines. Plain Markdown image-links, shields.io only for rendering. No workflow, config or script changes (R8). No ADR: nothing lasting is decided.

Why shields.io for everything: one familiar style, and the static badges need no workflow. The CI badge could use GitHub's native `badge.svg`, but mixing styles looks uneven, and shields' `github/actions/workflow/status` endpoint is stable.

## Files touched

Only `README.md`: lines added after line 1, none removed or edited.

## The row

Shape: `[![alt](image-url)](link-url)`. One badge per line, so the diff reads cleanly and a later badge is a one-line addition. Consecutive lines without blank lines render inline on one row.

| # | Alt | Image URL | Link |
|---|-----|-----------|------|
| 1 | CI | `https://img.shields.io/github/actions/workflow/status/bhoudebert/lookout/ci.yml?branch=main&label=CI` | `https://github.com/bhoudebert/lookout/actions/workflows/ci.yml` |
| 2 | Release | `https://img.shields.io/github/v/release/bhoudebert/lookout` | `https://github.com/bhoudebert/lookout/releases` |
| 3 | Python 3.13+ | `https://img.shields.io/badge/python-3.13%2B-3776AB?logo=python&logoColor=white` | `https://www.python.org/` |
| 4 | Node.js 24 | `https://img.shields.io/badge/node-24-339933?logo=nodedotjs&logoColor=white` | `https://nodejs.org/` |
| 5 | Conventional Commits 1.0.0 | `https://img.shields.io/badge/Conventional%20Commits-1.0.0-FE5196?logo=conventionalcommits&logoColor=white` | `https://www.conventionalcommits.org/en/v1.0.0/` |
| 6 | MIT licence | `https://img.shields.io/github/license/bhoudebert/lookout` | `LICENSE` (relative link) |

Notes:
- Order follows the request: health (CI), release, tech, process, licence.
- Python and Node values are copied from `pyproject.toml` (`requires-python = ">=3.13"`) and `.nvmrc` (`24`). They are typed by hand and can drift (accepted in the spec).
- The Python and Node links go to the project home pages. The spec requires only that every badge has a link.
- Badge 6 uses `github/license`, which asks the GitHub API to detect the licence. If that fails to read "MIT", fall back to the static `https://img.shields.io/badge/licence-MIT-blue`. This is the one implementation-time check.
- Badge 2 shows "no releases" until release-please cuts the first release (manifest is `0.0.0`). That is expected, not a bug.

## Errors and edge cases

- Private repo: the CI and release badges show as broken or unknown to anonymous readers. This is open question 2 in the spec. It needs the owner's answer, and the design does not depend on it. If the repo is private, the dynamic badges should be dropped or replaced with native GitHub ones.
- shields.io outage: images fail to load, alt text still reads correctly. Accepted.
- Renaming `ci.yml` breaks badge 1. Accepted in the spec.

## Testing

There is no test suite for README content, and adding one would exceed the scope. Verification is by inspection:

1. `git diff --stat` lists only `README.md`, with only added lines (R1, R8).
2. `grep -c 'bhoudebert/lookout' README.md` confirms each GitHub-derived URL names the repo (R7).
3. Every badge line has non-empty alt text and a link target (R7).
4. After the first push to `main`, open the README on GitHub and confirm the six badges render. Release shows "no releases" and the others resolve.
5. The repo's quality gate (`nix run .#quality`, including Prettier) must still pass. Prettier may check Markdown, so run it on `README.md`. Keep one badge per line with no wrapping, which Prettier's default `proseWrap: preserve` leaves alone. Check `.prettierrc.json` for overrides.

## Alternatives rejected

- **CodeQL badge and workflow:** dropped in the spec as too complex. It is a possible follow-up, open question 1.
- **Badges that read versions from the repo** (for example shields' dynamic JSON/TOML endpoints for `pyproject.toml` and `.nvmrc`): they avoid drift but are more complex and fragile. Dropped in the spec.
- **GitHub-native `badge.svg` for CI:** works, but the style differs from the other badges.
- **An HTML table or centred `<p align="center">` block:** more markup for no gain, and the diff is harder to read.
- **A new ADR:** nothing architectural is decided.
