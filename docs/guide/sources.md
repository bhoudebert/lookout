# Sources

A source is a river that flows into your inbox. It is declared in `lookout.yaml` with a unique name and a `type`, and says which [channels](/concepts) it may feed.

```yaml
sources:
  - name: python-insider
    type: rss
    url: https://pythoninsider.blogspot.com/feeds/posts/default
    channels: [Languages]
  - name: lobsters
    type: rss
    url: https://lobste.rs/rss
    keywords: [python, postgres, rust, security]
    enabled: true
```

`keywords` keeps only entries whose title or text contains one of them. `enabled: false` turns a source off.

`channels` lists the topics the source may feed: one means every item is filed there without asking the model, several (or none) lets the model choose among them. Each name must be declared under `channels`.

## What is supported today

The `rss` type reads RSS and Atom, keeps each entry's **author** and **tags**, and already covers a lot:

| You want                          | Use this feed                                            |
| --------------------------------- | -------------------------------------------------------- |
| A blog, news site, framework news | its RSS or Atom feed                                     |
| GitHub releases of a repository   | `https://github.com/OWNER/REPO/releases.atom`            |
| Reddit                            | `https://www.reddit.com/r/SUBREDDIT/.rss`                |
| Hacker News                       | `https://hnrss.org/frontpage`                            |
| A YouTube channel                 | `https://www.youtube.com/feeds/videos.xml?channel_id=ID` |

## GitHub: releases, security advisories, Dependabot

The `github` type reads repositories you name and gives advisories **structured data** (severity, package, identifiers), which is what the [priority rules](/priorities) need.

```yaml
sources:
  - name: my-repos
    type: github
    repos: [acme/api-service, acme/web]
    watch: [releases, advisories, dependabot] # default: releases and advisories
```

| Watch        | Reads                                                    | Needs                                      |
| ------------ | -------------------------------------------------------- | ------------------------------------------ |
| `releases`   | published releases (drafts skipped, pre-releases marked) | nothing special for public repositories    |
| `advisories` | published security advisories of the repository          | nothing special for public repositories    |
| `dependabot` | open Dependabot alerts                                   | access to the repository's security alerts |

An advisory or alert on a repository you list **counts as affecting your stack**: critical is at least P0, high at least P1, even if the package is not in your `stack`.

Lookout reaches GitHub with your local `gh` login when you have one (no token to store), otherwise with a token from `LOOKOUT_GITHUB_TOKEN` or `GITHUB_TOKEN`. Choose with `github.via` in the [configuration](/configuration). `lookout doctor` says which one is used. With neither, only the GitHub sources fail, with a message that says how to fix it.

## OSV: vulnerabilities for what you run

The `osv` type asks [OSV](https://osv.dev) about every entry of your `stack` whose ecosystem it covers (`pypi`, `npm`, `crates`, `go`), so advisories for packages you use arrive even from repositories you do not watch.

```yaml
stack:
  - name: django
    ecosystem: pypi
    version: "5.1.0" # quote it; OSV then returns only what affects this version
sources:
  - name: osv
    type: osv
    since_days: 30 # only vulnerabilities published in the last 30 days (default)
    kev: true # mark those CISA lists as exploited (default)
```

Severity is a fact, never the model's opinion: the database's own rating, else computed from the CVSS v3 vector, else moderate. A critical vulnerability on a package in your stack is **P0**, high is **P1**, and one that CISA lists in its _Known Exploited Vulnerabilities_ catalogue is **P0** whatever its rating. See [how priority is decided](/priorities).

Without a `version`, every recent vulnerability of the package is shown. Entries of other ecosystems (such as a database) are skipped; a stack with none OSV can use fails the source with a message saying so.

## Coming

Website-change watching, and dedicated Hacker News and Reddit adapters (scores, comment counts). See the [roadmap](https://github.com/bhoudebert/lookout/blob/main/ROADMAP.md).

## Politeness and failures

Lookout identifies itself with a User-Agent. A source that fails is recorded with its error and retried with growing delays (5 minutes, doubling, up to 6 hours); the other sources are never affected. `lookout doctor` and the Sources page show the last error.
