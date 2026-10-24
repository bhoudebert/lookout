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

## Coming

Dedicated adapters, so advisories carry structured severity and package data that feeds the [priority rules](/priorities): GitHub security advisories and Dependabot alerts (through your local `gh` login), OSV and NVD, and website-change watching. See the [roadmap](https://github.com/bhoudebert/lookout/blob/main/ROADMAP.md).

## Politeness and failures

Lookout identifies itself with a User-Agent. A source that fails is recorded with its error and retried with growing delays (5 minutes, doubling, up to 6 hours); the other sources are never affected. `lookout doctor` and the Sources page show the last error.
