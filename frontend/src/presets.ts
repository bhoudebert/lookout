/** Sources worth starting with: each address was checked to answer. One click adds the source and the categories it files in. */
export interface Preset {
  name: string;
  type: string;
  settings: Record<string, unknown>;
  /** What it brings, in a few words. */
  blurb: string;
  /** The category its items go to, created when missing; none lets the model choose. */
  category?: { name: string; description: string };
}

const RUST = { name: "Dev > Rust", description: "The Rust language and its ecosystem" };
const JAVA = { name: "Dev > Java", description: "Java, the JVM and its ecosystem" };
const AI = { name: "AI", description: "Models, agents and the tooling around them" };

export const PRESETS: Preset[] = [
  {
    name: "Hacker News",
    type: "hackernews",
    settings: { feed: "front_page", min_points: 100 },
    blurb: "Front page stories with at least 100 points",
  },
  {
    name: "Lobsters",
    type: "rss",
    settings: { url: "https://lobste.rs/rss" },
    blurb: "The hottest stories of the programmers' link site",
  },
  {
    name: "Rust Blog",
    type: "rss",
    settings: { url: "https://blog.rust-lang.org/feed.xml" },
    blurb: "Official: releases and announcements",
    category: RUST,
  },
  {
    name: "Inside Rust",
    type: "rss",
    settings: { url: "https://blog.rust-lang.org/inside-rust/feed.xml" },
    blurb: "Official: what the Rust teams are working on",
    category: RUST,
  },
  {
    name: "This Week in Rust",
    type: "rss",
    settings: { url: "https://this-week-in-rust.org/atom.xml" },
    blurb: "Weekly digest of the Rust community",
    category: RUST,
  },
  {
    name: "Inside Java",
    type: "rss",
    settings: { url: "https://inside.java/feed.xml" },
    blurb: "Official: news from the Java team at Oracle",
    category: JAVA,
  },
  {
    name: "Spring Blog",
    type: "rss",
    settings: { url: "https://spring.io/blog.atom" },
    blurb: "Spring releases and engineering posts",
    category: JAVA,
  },
  {
    name: "Simon Willison",
    type: "rss",
    settings: { url: "https://simonwillison.net/atom/everything/" },
    blurb: "A widely read, practical weblog on LLMs",
    category: AI,
  },
  {
    name: "Hugging Face Blog",
    type: "rss",
    settings: { url: "https://huggingface.co/blog/feed.xml" },
    blurb: "Open models, datasets and tooling",
    category: AI,
  },
  {
    name: "OpenAI News",
    type: "rss",
    settings: { url: "https://openai.com/news/rss.xml" },
    blurb: "Announcements from OpenAI",
    category: AI,
  },
  {
    name: "Latent Space",
    type: "rss",
    settings: { url: "https://www.latent.space/feed" },
    blurb: "Newsletter and podcast for AI engineers",
    category: AI,
  },
  {
    name: "Google Research",
    type: "rss",
    settings: { url: "https://research.google/blog/rss/" },
    blurb: "Research posts from Google",
    category: AI,
  },
];
