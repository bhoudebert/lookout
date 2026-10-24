import type { ActionResult, Item, ItemDetail, RunStatus, Source, Taxonomy } from "../api/types";

export function makeItem(overrides: Partial<Item> = {}): Item {
  return {
    id: "a1",
    url: "https://example.test/a1",
    title: "Django 6.0 released",
    summary: "Django 6.0 is out.",
    excerpt: "Django 6.0 is out.",
    published_at: "2026-10-24T08:00:00Z",
    sources: ["blog"],
    kind: "release",
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
      { name: "AI", description: "Models" },
      { name: "Rust", description: "" },
      { name: "Other", description: "" },
    ],
    kinds: ["release", "security", "tooling"],
  };
  run: RunStatus = IDLE;
  runPolls = 0;
  calls: Call[] = [];
  failWith: { status: number; detail: unknown } | null = null;
  unreachable = false;
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
    if (path.startsWith("/api/sources/"))
      return this.patchSource(decodeURIComponent(path.slice(13)), body as { enabled: boolean });
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
        (!params.get("channel") || i.channel === params.get("channel")) &&
        (!params.get("kind") || i.kind === params.get("kind")) &&
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

  private patchSource(name: string, body: { enabled: boolean }): Response {
    const source = this.sources.find((s) => s.name === name) as Source;
    source.enabled = body.enabled;
    return this.json(source);
  }
}
