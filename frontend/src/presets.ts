/** Sources worth starting with. Each address was fetched and answered; one click adds the source and its category. */
export interface Category {
  name: string;
  description: string;
}

export interface Preset {
  name: string;
  type: string;
  settings: Record<string, unknown>;
  /** What it brings, in a few words. */
  blurb: string;
  group: string;
  /** The category its items go to, created when missing; none lets the model choose. */
  category?: Category;
}

export interface Group {
  id: string;
  title: string;
  /** What the group is, shown when it is opened. */
  about: string;
}

export const GROUPS: Group[] = [
  { id: "links", title: "Link sites", about: "What programmers are reading and discussing." },
  { id: "rust", title: "Rust", about: "Official news and the community digest." },
  { id: "java", title: "Java", about: "News from the Java team and the Spring project." },
  { id: "ai", title: "AI blogs", about: "Practical writing and announcements on models and agents." },
  {
    id: "security",
    title: "Security",
    about: "Vulnerabilities of what you run. Needs your `stack` declared in lookout.yaml.",
  },
  {
    id: "status",
    title: "Service status",
    about: "Outages and incidents of the services you depend on, as they are reported.",
  },
  {
    id: "reddit",
    title: "Reddit communities",
    about:
      "Several communities in one source, one request. Reddit allows about one request a minute, so each source of this kind takes about a minute of a run. No scores: Reddit does not share them anonymously.",
  },
  { id: "youtube", title: "YouTube channels", about: "The recent videos of one channel each." },
  { id: "france", title: "News: France", about: "French news, politics and the economy." },
  { id: "world", title: "News: world and politics", about: "International news and European politics." },
  { id: "tech-news", title: "Tech news in French", about: "Technology and the internet, in French." },
];

const RUST: Category = { name: "Dev > Rust", description: "The Rust language and its ecosystem" };
const JAVA: Category = { name: "Dev > Java", description: "Java, the JVM and its ecosystem" };
const OPS: Category = { name: "Dev > Ops", description: "Operations, infrastructure and self-hosting" };
const DEV: Category = { name: "Dev", description: "Software development" };
const AI: Category = { name: "AI", description: "Models, agents and the tooling around them" };
const SECURITY: Category = { name: "Security", description: "Vulnerabilities and fixes in what I run" };
const STATUS: Category = { name: "Status", description: "Outages and incidents of the services I depend on" };
const FRANCE: Category = { name: "News > France", description: "News from France" };
const POLITICS: Category = { name: "News > Politics", description: "Political news" };
const WORLD: Category = { name: "News > World", description: "International news" };
const TECH: Category = { name: "Tech", description: "Technology and the internet" };

const feed = (group: string, name: string, url: string, blurb: string, category?: Category): Preset => ({
  name,
  type: "rss",
  settings: { url },
  blurb,
  group,
  category,
});

const reddit = (name: string, subreddits: string[], blurb: string, category: Category): Preset => ({
  name,
  type: "reddit",
  settings: { subreddits, sort: "hot" },
  blurb,
  group: "reddit",
  category,
});

const channel = (name: string, handle: string, blurb: string, category: Category): Preset => ({
  name: `YouTube: ${name}`,
  type: "youtube",
  settings: { channel: handle },
  blurb,
  group: "youtube",
  category,
});

export const PRESETS: Preset[] = [
  {
    name: "Hacker News",
    type: "hackernews",
    settings: { feed: "front_page", min_points: 100 },
    blurb: "Front page stories with at least 100 points",
    group: "links",
  },
  feed(
    "links",
    "Lobsters: hottest",
    "https://lobste.rs/rss",
    "The 25 stories Lobsters ranks highest now. A new story shows up only once it gains votes",
  ),
  feed(
    "links",
    "Lobsters: newest",
    "https://lobste.rs/newest.rss",
    'The 25 most recent stories, in order, whatever their votes (the site\'s "newest" tab)',
  ),

  feed("rust", "Rust Blog", "https://blog.rust-lang.org/feed.xml", "Official: releases and announcements", RUST),
  feed(
    "rust",
    "Inside Rust",
    "https://blog.rust-lang.org/inside-rust/feed.xml",
    "Official: what the Rust teams work on",
    RUST,
  ),
  feed(
    "rust",
    "This Week in Rust",
    "https://this-week-in-rust.org/atom.xml",
    "Weekly digest of the Rust community",
    RUST,
  ),

  feed("java", "Inside Java", "https://inside.java/feed.xml", "Official: news from the Java team at Oracle", JAVA),
  feed("java", "Spring Blog", "https://spring.io/blog.atom", "Spring releases and engineering posts", JAVA),

  feed(
    "ai",
    "Simon Willison",
    "https://simonwillison.net/atom/everything/",
    "A widely read, practical weblog on LLMs",
    AI,
  ),
  feed("ai", "Hugging Face Blog", "https://huggingface.co/blog/feed.xml", "Open models, datasets and tooling", AI),
  feed("ai", "OpenAI News", "https://openai.com/news/rss.xml", "Announcements from OpenAI", AI),
  feed("ai", "Latent Space", "https://www.latent.space/feed", "Newsletter and podcast for AI engineers", AI),
  feed("ai", "Google Research", "https://research.google/blog/rss/", "Research posts from Google", AI),

  {
    name: "OSV vulnerabilities",
    type: "osv",
    settings: { since_days: 30, kev: true },
    blurb: "Vulnerabilities of the packages in your stack, with CISA's known-exploited flag",
    group: "security",
    category: SECURITY,
  },

  feed("status", "GitHub status", "https://www.githubstatus.com/history.atom", "Incidents on GitHub", STATUS),
  feed(
    "status",
    "Google Cloud status",
    "https://status.cloud.google.com/en/feed.atom",
    "Incidents on Google Cloud",
    STATUS,
  ),
  feed(
    "status",
    "Cloudflare status",
    "https://www.cloudflarestatus.com/history.atom",
    "Incidents at Cloudflare",
    STATUS,
  ),
  feed(
    "status",
    "OpenAI status",
    "https://status.openai.com/feed.atom",
    "Incidents on the OpenAI API and ChatGPT",
    STATUS,
  ),
  feed(
    "status",
    "Anthropic status",
    "https://status.anthropic.com/history.atom",
    "Incidents on the Claude API",
    STATUS,
  ),
  feed("status", "Vercel status", "https://www.vercel-status.com/history.atom", "Incidents on Vercel", STATUS),
  feed("status", "npm status", "https://status.npmjs.org/history.atom", "Incidents on the npm registry", STATUS),
  feed("status", "AWS status", "https://status.aws.amazon.com/rss/all.rss", "Incidents on every AWS service", STATUS),
  feed("status", "Azure status", "https://azure.status.microsoft/en-us/status/feed/", "Incidents on Azure", STATUS),
  feed("status", "Slack status", "https://status.slack.com/feed/rss", "Incidents on Slack", STATUS),
  feed(
    "status",
    "DigitalOcean status",
    "https://status.digitalocean.com/history.atom",
    "Incidents at DigitalOcean",
    STATUS,
  ),

  reddit(
    "Reddit: programming",
    ["programming", "rust", "java", "python", "golang", "webdev"],
    "r/programming, rust, java, python, golang, webdev",
    DEV,
  ),
  reddit(
    "Reddit: AI",
    ["LocalLLaMA", "MachineLearning", "ClaudeAI", "OpenAI"],
    "r/LocalLLaMA, MachineLearning, ClaudeAI, OpenAI",
    AI,
  ),
  reddit("Reddit: security", ["netsec", "cybersecurity"], "r/netsec, cybersecurity", SECURITY),
  reddit(
    "Reddit: ops",
    ["devops", "selfhosted", "sysadmin", "kubernetes"],
    "r/devops, selfhosted, sysadmin, kubernetes",
    OPS,
  ),
  reddit("Reddit: France", ["france", "programmation"], "r/france, programmation", FRANCE),

  channel("Fireship", "@fireship", "Short, fast explainers on the tools of the week", DEV),
  channel("ThePrimeagen", "@ThePrimeagen", "Opinionated engineering, editors and languages", DEV),
  channel("Computerphile", "@Computerphile", "Computer science explained", DEV),
  channel("ArjanCodes", "@ArjanCodes", "Software design in Python", DEV),
  channel("Java", "@java", "The official Java channel", JAVA),
  channel("LiveOverflow", "@LiveOverflow", "Hacking and security, explained", SECURITY),
  channel("NetworkChuck", "@NetworkChuck", "Networking and security for everyone", SECURITY),
  channel("Underscore_", "@Underscore_", "Technology and the internet, in French", TECH),

  feed("france", "Le Monde", "https://www.lemonde.fr/rss/une.xml", "The front page", FRANCE),
  feed("france", "franceinfo", "https://www.francetvinfo.fr/titres.rss", "Headlines of the public broadcaster", FRANCE),
  feed("france", "France 24", "https://www.france24.com/fr/rss", "International news from France", FRANCE),
  feed("france", "Le Figaro", "https://www.lefigaro.fr/rss/figaro_actualites.xml", "Headlines", FRANCE),
  feed(
    "france",
    "Libération",
    "https://www.liberation.fr/arc/outboundfeeds/rss-all/collection/accueil-une/",
    "The front page",
    FRANCE,
  ),
  feed("france", "RFI", "https://www.rfi.fr/fr/rss", "Radio France Internationale", FRANCE),
  feed("france", "Le Monde: économie", "https://www.lemonde.fr/economie/rss_full.xml", "The economy", FRANCE),
  feed("france", "Le Monde: politique", "https://www.lemonde.fr/politique/rss_full.xml", "French politics", POLITICS),

  feed("world", "BBC World", "https://feeds.bbci.co.uk/news/world/rss.xml", "World news from the BBC", WORLD),
  feed("world", "The Guardian: world", "https://www.theguardian.com/world/rss", "World news from the Guardian", WORLD),
  feed("world", "Politico Europe", "https://www.politico.eu/feed/", "European politics", POLITICS),

  feed("tech-news", "Numerama", "https://www.numerama.com/feed/", "Technology, science and culture", TECH),
  feed("tech-news", "Korben", "https://korben.info/feed", "Tools, tips and the internet", TECH),
  feed("tech-news", "01net", "https://www.01net.com/feed/", "Consumer and business tech", TECH),
  feed("tech-news", "Le Monde: Pixels", "https://www.lemonde.fr/pixels/rss_full.xml", "Digital and video games", TECH),
];
