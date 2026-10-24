import type { ActionResult, Channel, Item, ItemDetail, RunStatus, Source, SourceType, Taxonomy } from "../api/types";

export function makeItem(overrides: Partial<Item> = {}): Item {
  return {
    id: "a1",
    url: "https://example.test/a1",
    title: "Django 6.0 released",
    summary: "Django 6.0 is out.",
    excerpt: "Django 6.0 is out.",
    published_at: "2026-10-24T08:00:00Z",
    sources: ["blog"],
    channel: "Other",
    author: "",
    feed_tags: [],
    tags: ["django"],
    priority: "P1",
    priority_label: "this week",
    priority_reason: "model score 75: you use Django",
    action_needed: false,
    state: "new",
    snoozed_until: null,
    starred: false,
    stack_matches: [],
    enrichment_failed: false,
    unread: false,
    score: 75,
    boost: 0,
    ...overrides,
  };
}

export function makeSource(overrides: Partial<Source> = {}): Source {
  return {
    name: "blog",
    type: "rss",
    enabled: true,
    channels: [],
    keywords: [],
    settings: { url: "https://example.test/feed" },
    last_run: "2026-10-24T08:00:00Z",
    last_error: null,
    items_seen: 3,
    ...overrides,
  };
}

const IDLE: RunStatus = {
  running: false,
  started: false,
  started_at: null,
  finished_at: null,
  error: null,
  sources: [],
  enriched: 0,
  failed: 0,
  waiting: 0,
};

interface Call {
  method: string;
  path: string;
  body: unknown;
}

/** An in-memory stand-in for the Lookout API, good enough to drive every screen. */
export class FakeBackend {
  items: Item[];
  sources: Source[];
  taxonomy: Taxonomy = {
    channels: [
      { name: "AI", description: "Models", items: 2, sources: ["blog"] },
      { name: "Dev", description: "", items: 0, sources: [] },
      { name: "Dev > Rust", description: "", items: 1, sources: [] },
      { name: "Other", description: "", items: 0, sources: [] },
    ],
  };
  sourceTypes: SourceType[] = [
    {
      name: "rss",
      label: "RSS or Atom feed",
      description: "Blogs and news.",
      fields: [
        { name: "url", label: "Feed address", kind: "text", required: true, default: null, help: "https://..." },
      ],
    },
    {
      name: "github",
      label: "GitHub repositories",
      description: "Releases and advisories.",
      fields: [
        {
          name: "repos",
          label: "Repositories",
          kind: "list",
          required: true,
          default: null,
          help: "owner/name, one per line",
        },
        {
          name: "watch",
          label: "Watch",
          kind: "list",
          required: false,
          default: ["releases", "advisories"],
          help: "what to read",
        },
      ],
    },
    {
      name: "osv",
      label: "OSV vulnerabilities",
      description: "Vulnerabilities of your stack.",
      fields: [
        { name: "since_days", label: "Only the last (days)", kind: "number", required: false, default: 30, help: "" },
        { name: "kev", label: "Flag CISA known-exploited", kind: "bool", required: false, default: true, help: "" },
      ],
    },
  ];
  refiled = { filed: 2, queued: 5 };
  run: RunStatus = IDLE;
  runPolls = 0;
  calls: Call[] = [];
  failWith: { status: number; detail: unknown } | null = null;
  unreachable = false;
  /** Answer 500 to the paths starting with this, and normally to the others. */
  failOn: string | null = null;
  detail: Partial<ItemDetail> = {};
  private undo = new Map<string, Item>();

  constructor(items: Item[] = [], sources: Source[] = [makeSource()]) {
    this.items = items;
    this.sources = sources;
  }

  readonly fetch = (input: string | URL, init?: RequestInit): Promise<Response> => {
    if (this.unreachable) return Promise.reject(new TypeError("network down"));
    const url = new URL(input, "http://lookout.test");
    const method = init?.method ?? "GET";
    const body: unknown = typeof init?.body === "string" ? JSON.parse(init.body) : undefined;
    this.calls.push({ method, path: url.pathname + url.search, body });
    if (this.failOn && url.pathname.startsWith(this.failOn)) {
      return Promise.resolve(new Response(JSON.stringify({ detail: "broken" }), { status: 500 }));
    }
    if (this.failWith) {
      const { status, detail } = this.failWith;
      return Promise.resolve(new Response(JSON.stringify({ detail }), { status }));
    }
    return Promise.resolve(this.route(method, url, body));
  };

  private json(data: unknown, status = 200): Response {
    return new Response(JSON.stringify(data), { status });
  }

  private route(method: string, url: URL, body: unknown): Response {
    const path = url.pathname;
    const id = /^\/api\/items\/([^/]+)/.exec(path)?.[1];
    if (path === "/api/items" && method === "GET") return this.list(url.searchParams);
    if (path === "/api/items/bulk") return this.bulk(body as { ids: string[]; action: string });
    if (path === "/api/items/seen-below") return this.seenBelow();
    if (id && path.endsWith("/actions")) return this.act(id, body as { action: string; hours?: number });
    if (id && path.endsWith("/restore"))
      return this.restore(id, body as Pick<Item, "state" | "snoozed_until" | "starred">);
    if (id && method === "GET") return this.one(id);
    if (path === "/api/taxonomy") return this.json(this.taxonomy);
    if (path === "/api/sources" && method === "GET") return this.json(this.sources);
    if (path === "/api/source-types") return this.json(this.sourceTypes);
    if (path === "/api/sources" && method === "POST") return this.addSource(body as Partial<Source>);
    if (path.startsWith("/api/sources/"))
      return this.changeSource(method, decodeURIComponent(path.slice(13)), body as Partial<Source>);
    if (path === "/api/channels" && method === "POST") return this.addChannel(body as Channel);
    if (path === "/api/refile") return this.json(this.refiled);
    if (path.startsWith("/api/channels/"))
      return this.changeChannel(method, decodeURIComponent(path.slice(14)), body as Partial<Channel>);
    if (path === "/api/run" && method === "POST") {
      this.run = { ...IDLE, running: true, started: true, started_at: "2026-10-24T09:00:00Z" };
      return this.json(this.run, 202);
    }
    if (path === "/api/run") {
      if (this.run.running && ++this.runPolls >= 2) {
        this.run = {
          ...IDLE,
          finished_at: "2026-10-24T09:00:05Z",
          enriched: 3,
          sources: [{ name: "blog", fetched: 3, new: 3, error: null, skipped: false }],
        };
      }
      return this.json(this.run);
    }
    return this.json({ detail: "not found" }, 404);
  }

  private list(params: URLSearchParams): Response {
    const states = params.getAll("state");
    const wanted = states.length > 0 ? states : ["new", "seen"];
    const priorities = params.getAll("priority");
    const text = (params.get("text") ?? "").toLowerCase();
    const matches = this.items.filter(
      (i) =>
        wanted.includes(i.state) &&
        (priorities.length === 0 || priorities.includes(i.priority)) &&
        (!params.get("channel") ||
          i.channel === params.get("channel") ||
          i.channel.startsWith(`${params.get("channel")} > `)) &&
        (!params.get("source") || i.sources.includes(params.get("source") as string)) &&
        (params.get("starred") !== "true" || i.starred) &&
        (!text || `${i.title} ${i.author}`.toLowerCase().includes(text)),
    );
    return this.json({ items: matches, total: matches.length });
  }

  private one(id: string): Response {
    const item = this.items.find((i) => i.id === id);
    if (!item) return this.json({ detail: `no item ${id}` }, 404);
    const detail: ItemDetail = {
      item,
      body: `Full text of ${item.title}`,
      explanation: {
        priority: item.priority,
        priority_reason: item.priority_reason,
        model_score: item.score,
        boost: item.boost,
        contributions: [],
      },
      ...this.detail,
    };
    return this.json(detail);
  }

  private act(id: string, body: { action: string; hours?: number }): Response {
    const item = this.items.find((i) => i.id === id);
    if (!item) return this.json({ detail: `no item ${id}` }, 404);
    const before = { ...item };
    const next: Partial<Item> =
      {
        open: item.state === "new" ? { state: "seen" as const } : {},
        done: { state: "done" as const },
        dismiss: { state: "dismissed" as const },
        snooze: { state: "snoozed" as const, snoozed_until: "2026-10-25T09:00:00Z" },
        reopen: { state: "seen" as const },
        star: { starred: true },
        unstar: { starred: false },
      }[body.action] ?? {};
    Object.assign(item, next);
    this.undo.set(id, before);
    const result: ActionResult = {
      item,
      undo: { state: before.state, snoozed_until: before.snoozed_until, starred: before.starred },
    };
    return this.json(result);
  }

  private restore(id: string, back: Pick<Item, "state" | "snoozed_until" | "starred">): Response {
    const item = this.items.find((i) => i.id === id) as Item;
    Object.assign(item, back);
    return this.json(item);
  }

  private bulk(body: { ids: string[]; action: string }): Response {
    const state = { done: "done", dismiss: "dismissed", snooze: "snoozed" }[body.action] as Item["state"];
    for (const item of this.items) if (body.ids.includes(item.id)) item.state = state;
    return this.json({ changed: body.ids.length });
  }

  private seenBelow(): Response {
    const low = this.items.filter((i) => i.state === "new" && (i.priority === "P2" || i.priority === "P3"));
    for (const item of low) item.state = "seen";
    return this.json({ changed: low.length });
  }

  private addSource(body: Partial<Source>): Response {
    const source = makeSource({ items_seen: 0, last_run: null, ...body });
    this.sources.push(source);
    return this.json(source, 201);
  }

  private changeSource(method: string, name: string, body: Partial<Source>): Response {
    const index = this.sources.findIndex((s) => s.name === name);
    if (method === "DELETE") {
      this.sources.splice(index, 1);
      return new Response(null, { status: 204 });
    }
    const source = this.sources[index] as Source;
    Object.assign(source, body);
    return this.json(source);
  }

  private addChannel(body: Channel): Response {
    this.taxonomy.channels.push({ ...body, items: 0, sources: [] });
    return this.json(body, 201);
  }

  private changeChannel(method: string, name: string, body: Partial<Channel>): Response {
    const index = this.taxonomy.channels.findIndex((c) => c.name === name);
    if (method === "DELETE") {
      this.taxonomy.channels.splice(index, 1);
      return new Response(null, { status: 204 });
    }
    const channel = this.taxonomy.channels[index] as Channel;
    Object.assign(channel, body);
    return this.json(channel);
  }
}
