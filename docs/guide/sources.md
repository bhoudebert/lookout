# Sources

A source is declared in `lookout.yaml` with a unique name and a kind.

```yaml
sources:
  - name: python-insider
    kind: rss
    url: https://pythoninsider.blogspot.com/feeds/posts/default
  - name: lobsters
    kind: rss
    url: https://lobste.rs/rss
    keywords: [python, postgres, rust, security]
    enabled: true
```

`keywords` keeps only entries whose title or text contains one of them. `enabled: false` turns a source off.

## What is supported today

The `rss` kind reads RSS and Atom, which already covers a lot:

| You want                          | Use this feed                                            |
| --------------------------------- | -------------------------------------------------------- |
| A blog, news site, framework news | its RSS or Atom feed                                     |
| GitHub releases of a repository   | `https://github.com/OWNER/REPO/releases.atom`            |
| Reddit                            | `https://www.reddit.com/r/SUBREDDIT/.rss`                |
| Hacker News                       | `https://hnrss.org/frontpage`                            |
| A YouTube channel                 | `https://www.youtube.com/feeds/videos.xml?channel_id=ID` |

## GitHub: releases, security advisories, Dependabot

The `github` kind reads repositories you name and gives advisories **structured data** (severity, package, identifiers), which is what the [priority rules](/priorities) need.

```yaml
sources:
  - name: my-repos
    kind: github
    repos: [acme/api-service, acme/web]
    kinds: [releases, advisories, dependabot] # default: releases and advisories
```

| Kind         | Reads                                                    | Needs                                      |
| ------------ | -------------------------------------------------------- | ------------------------------------------ |
| `releases`   | published releases (drafts skipped, pre-releases marked) | nothing special for public repositories    |
| `advisories` | published security advisories of the repository          | nothing special for public repositories    |
| `dependabot` | open Dependabot alerts                                   | access to the repository's security alerts |

An advisory or alert on a repository you list **counts as affecting your stack**: critical is at least P0, high at least P1, even if the package is not in your `stack`.

Lookout reaches GitHub with your local `gh` login when you have one (no token to store), otherwise with a token from `LOOKOUT_GITHUB_TOKEN` or `GITHUB_TOKEN`. Choose with `github.via` in the [configuration](/configuration). `lookout doctor` says which one is used. With neither, only the GitHub sources fail, with a message that says how to fix it.

## Coming

OSV and NVD, so advisories for packages in your stack arrive even from repositories you do not watch, and website-change watching. Dedicated Hacker News and Reddit adapters are planned too. See the [roadmap](https://github.com/bhoudebert/lookout/blob/main/ROADMAP.md).

## Politeness and failures

Lookout identifies itself with a User-Agent. A source that fails is recorded with its error and retried with growing delays (5 minutes, doubling, up to 6 hours); the other sources are never affected. `lookout doctor` and the Sources page show the last error.
