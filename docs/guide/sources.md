# Sources

Sources are the **rivers** that flow into your inbox; [categories](/concepts) are the places they flow to. Sources are managed on the **Sources** page, categories on the **Categories** page.

## In the dashboard

- **Add a source**: pick its type, fill the settings that type needs (the form is built from the type), tick the categories it may feed (or create one right there: a source that mixes topics, like a Reddit source on Rust and on motorcycles, is better split in two, each filed in its own category, so the model does not have to choose), add keywords if you want to keep only some entries. A source is checked when you save it: a bad address or an unknown repository is refused with the reason, and nothing is stored.
- **Edit** any setting except the name and the type. **Switch** a source on or off. **Delete** a source: its items stay in your inbox.
- **Categories** are managed on their own page. A category a source still feeds cannot be deleted, and the message names those sources.
- A new or changed source is used by the **next run**, with no restart.

### The file only seeds

`lookout.yaml` is read for its `sources`, `channels` (your categories) **once**, on the very first start, to fill the dashboard. After that the dashboard is the truth, and changing those lists in the file does nothing (deleting every source does not bring them back either). The rest of the file (the model, your stack, thresholds) is still read at every start.

The examples below are what the file and the dashboard both accept.

A source is a river that flows into your inbox. It is declared in `lookout.yaml` with a unique name and a `type`, and says which [categories](/concepts) it may feed.

```yaml
sources:
  - name: python-insider
    type: rss
    url: https://pythoninsider.blogspot.com/feeds/posts/default
    channels: [Dev > Python]
  - name: lobsters
    type: rss
    url: https://lobste.rs/rss
    keywords: [python, postgres, rust, security]
    enabled: true
```

`keywords` keeps only the entries whose title or text mentions one of them. `enabled: false` turns a source off.

Keywords are matched as **whole words**, ignoring case, accents and markup:

| Keyword           | Finds                                                     | Does not find        |
| ----------------- | --------------------------------------------------------- | -------------------- |
| `moto`            | Moto, moto-cross, "casque moto"                           | Motorola, automotive |
| `vélo*`           | vélo, vélos, VÉLO, "velo" (the star lets the word run on) | "développement"      |
| `vélo électrique` | vélo électrique, vélo-électrique (a phrase)               | "vélo ou électrique" |
| `-motorola`       | (drops any entry that mentions it)                        |                      |

An entry is kept when it has at least one plain keyword (or there are none) and none of the excluded ones. Before this change keywords matched any part of a word, so `moto` also found Motorola.

`channels` lists the categories the source may feed (the file and the API call them channels): one means every item is filed there without asking the model, several (or none) lets the model choose among them. Each name must be declared under `channels`.

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

The `github` type reads repositories you name and gives advisories **structured data** (severity, package, identifiers), which is what the [priority rules](/priorities) need. Write each repository as `owner/name`, or paste its address (`https://github.com/owner/name`, with or without a trailing slash or `.git`, or the SSH form); Lookout keeps `owner/name`.

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

## What a feed gives you

A feed is a window, not an archive: a fixed number of entries (often 25), chosen by the site. Which entries depends on the
address. Lobsters' `/rss` is its **hottest** ranking, so a story posted a minute ago is missing until it gets votes; its
`/newest.rss` lists the most recent ones in order. Reddit's `hot` and `new` differ the same way. If a site has both, choose by
what you want: hottest for what the community found worth reading, newest to miss nothing. Lookout stores each entry once, so
watching both costs nothing in duplicates.

## Hacker News

The `hackernews` type reads stories through [Hacker News's search API](https://hn.algolia.com/api), with their points and comments (the item carries the link to the discussion; an Ask HN, which has no address of its own, is the discussion itself).

```yaml
sources:
  - name: hacker news
    type: hackernews
    feed: front_page # front_page (default), newest, ask or show
    min_points: 100 # only stories with at least this many points (default 0)
    limit: 30 # stories per run, 1 to 100 (default 30)
    keywords: [rust, security] # optional, like any source
```

## Reddit

The `reddit` type reads several communities in **one** request, so keep your subreddits together in one source:

```yaml
sources:
  - name: reddit dev
    type: reddit
    subreddits: [programming, rust, r/java, https://www.reddit.com/r/python/] # names, r/names or addresses
    sort: hot # hot (default) or new
    limit: 100 # posts per run, 1 to 100 (default 100)
```

Reddit lets an anonymous client make about **one request a minute**. When it says to slow down, the source waits as
long as Reddit asks (up to 90 seconds) and tries once more. Each Reddit source therefore costs about a minute of a run,
which is another reason to group communities. Reddit shares **no scores or comment counts** with anonymous clients, so
posts are ranked by the model and your profile, not by votes.

## YouTube

The `youtube` type follows one channel. Give its `@handle`, its address, or its id; Lookout finds the feed:

```yaml
sources:
  - name: fireship
    type: youtube
    channel: "@fireship" # or https://www.youtube.com/@fireship, or UCsBjURrPoezykLs9EqgamOA
```

A channel is a person or an organisation; there is no "all of YouTube". Add one source per channel you want.

## Deals

Dealabs publishes one feed per category, and each holds only its **30 latest deals**: the whole site (`/rss/tous`) is about 47 minutes, a busy category like High-Tech about 11 hours, a quiet one a few days. So the busy feeds need a frequent run (`schedule.interval_minutes: 30`), and the category feeds are best because they filter for free. Pick them by what you want:

- **No model needed:** a feed filed in **one** category (High-Tech into `Commerce > Deals > IT`, Auto-Moto into `… > Moto`) never asks the model to choose.
- **Keywords on the whole site:** the **Cycling** suggestion reads every new deal and keeps those that mention a bike, for the topics Dealabs has no category for.
- **Let the model sort:** file a source under the parent `Commerce > Deals` (the **Hot** suggestion does) and the model chooses the most specific child (IT, Moto, Cycling, …) for each deal, using your daily model limit.

The price and the shop are in the text of each deal ("9,99€ - Veepee"), and the search box finds them.

## Suggested sources

The **Sources** page suggests sources to start with, grouped by theme and collapsed until you open one. Each address was
checked. One click adds the source and, if it does not exist yet, the category it files in.

- **Link sites:** Hacker News (100+ points), and Lobsters twice: **hottest** (what the site ranks highest, a story appears once it gains votes) and **newest** (the most recent stories in order). Pick the one you mean, or both.
- **Rust, Java, AI blogs:** the official Rust blog, Inside Rust and This Week in Rust; Inside Java and the Spring blog;
  Simon Willison, Hugging Face, OpenAI, Latent Space and Google Research.
- **Security:** OSV vulnerabilities (filed in `Security`; it needs your `stack` in `lookout.yaml`).
- **Service status:** GitHub, Google Cloud, Cloudflare, OpenAI, Anthropic, Vercel, npm, AWS, Azure, Slack and
  DigitalOcean, filed in `Status`.
- **Reddit communities:** programming, AI, security, ops and France, each several communities in one source.
- **YouTube channels:** Fireship, ThePrimeagen, Computerphile, ArjanCodes, Java, LiveOverflow, NetworkChuck and
  Underscore_.
- **Deals (Dealabs):** one feed per Dealabs category (High-Tech, Auto-Moto, games, home, garden, fashion, culture, family, travel), each filed under `Commerce > Deals > ...`, plus the hottest deals and a **Cycling** source made of the all-deals feed filtered on bike keywords. Entries older than 3 days are not stored. See below.
- **News:** French news (Le Monde, franceinfo, France 24, Le Figaro, Libération, RFI), politics, world news (BBC, the
  Guardian, Politico Europe) and French tech news, filed under `News > ...` and `Tech`.

## Coming

Website-change watching, and GitHub issues, pull requests and discussions. See the [roadmap](https://github.com/bhoudebert/lookout/blob/main/ROADMAP.md).

## Politeness and failures

Lookout identifies itself with a User-Agent. A source that fails is recorded with its error and retried with growing delays (5 minutes, doubling, up to 6 hours); the other sources are never affected. `lookout doctor` and the Sources page show the last error.
