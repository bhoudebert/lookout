import type {
  ActionResult,
  Channel,
  Digest,
  Item,
  ItemDetail,
  RunStatus,
  Source,
  SourceType,
  Taxonomy,
} from "../api/types";

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
    rating: 0,
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

interface Filter {
  state: string[];
  priority: string[];
  channel: string[];
  source: string[];
  starred: boolean | null;
  text: string;
  older_than_days: number | null;
  newer_than_days: number | null;
}

/** An in-memory stand-in for the Lookout API, good enough to drive every screen. */
export class FakeBackend {
  items: Item[];
  sources: Source[];
  taxonomy: Taxonomy = {
    channels: [
      { name: "AI", description: "Models", icon: "🤖", items: 2, sources: ["blog"] },
      { name: "Dev", description: "", icon: "", items: 0, sources: [] },
      { name: "Dev > Rust", description: "", icon: "", items: 1, sources: [] },
      { name: "Other", description: "", icon: "", items: 0, sources: [] },
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
  digests: Digest[] = [];
  digestFails: string | null = null;
  /** While set, writing a digest waits for it, like a model that takes its time. */
  digestGate: Promise<void> | null = null;
  iconsSuggested = { suggested: 2, failed: false };
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
    if (this.digestGate && method === "POST" && url.pathname === "/api/digests") {
      return this.digestGate.then(() => this.route(method, url, body));
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
    if (path === "/api/items/sweep") return this.sweep(body as Parameters<FakeBackend["sweep"]>[0]);
    if (path === "/api/items/bulk-rating") return this.rateMany(body as { ids: string[]; rating: number });
    if (path === "/api/items/restore-many") return this.restoreMany(body as Parameters<FakeBackend["restoreMany"]>[0]);
    if (path === "/api/items/bulk") return this.bulk(body as { ids: string[]; action: string });
    if (path === "/api/items/seen-below") return this.seenBelow();
    if (id && path.endsWith("/actions")) return this.act(id, body as { action: string; hours?: number });
    if (id && path.endsWith("/restore"))
      return this.restore(id, body as Pick<Item, "state" | "snoozed_until" | "starred" | "rating">);
    if (id && path.endsWith("/rating")) return this.rate(id, body as { rating: number });
    if (id && method === "GET") return this.one(id);
    if (path === "/api/taxonomy") return this.json(this.counted(url.searchParams));
    if (path === "/api/sources" && method === "GET") return this.json(this.sources);
    if (path === "/api/source-types") return this.json(this.sourceTypes);
    if (path === "/api/sources" && method === "POST") return this.addSource(body as Partial<Source>);
    if (path.startsWith("/api/sources/"))
      return this.changeSource(method, decodeURIComponent(path.slice(13)), body as Partial<Source>);
    if (path === "/api/channels" && method === "POST")
      return this.addChannel(body as Partial<Channel> & { name: string });
    if (path === "/api/digests" && method === "POST") return this.makeDigest(body as { filter: { text: string } });
    if (path === "/api/digests") return this.json(this.digests);
    if (path.startsWith("/api/digests/")) return this.oneDigest(method, decodeURIComponent(path.slice(13)));
    if (path === "/api/refile") return this.json(this.refiled);
    if (path === "/api/channels/icons") return this.json(this.iconsSuggested);
    if (path.startsWith("/api/channels/") && path.endsWith("/move"))
      return this.moveChannel(decodeURIComponent(path.slice(14, -5)), (body as { parent: string }).parent);
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
    const channel = params.get("channel");
    const source = params.get("source");
    const older = params.get("older_than_days");
    const newer = params.get("newer_than_days");
    const matches = this.matching({
      state: wanted,
      priority: priorities,
      channel: channel ? [channel] : [],
      source: source ? [source] : [],
      starred: params.get("starred") === "true" ? true : null,
      text: params.get("text") ?? "",
      older_than_days: older ? Number(older) : null,
      newer_than_days: newer ? Number(newer) : null,
    });
    const newest = (a: Item, b: Item) => b.published_at.localeCompare(a.published_at);
    matches.sort(
      params.get("order") === "date" ? newest : (a, b) => a.priority.localeCompare(b.priority) || newest(a, b),
    );
    const offset = Number(params.get("offset") ?? 0);
    const limit = Number(params.get("limit") ?? 50);
    return this.json({ items: matches.slice(offset, offset + limit), total: matches.length });
  }

  /** The categories with the items the same filters would list in each, like the server. */
  private counted(params: URLSearchParams): Taxonomy {
    const wanted = params.getAll("state");
    const older = params.get("older_than_days");
    const newer = params.get("newer_than_days");
    const source = params.get("source");
    const found = this.matching({
      state: wanted,
      priority: params.getAll("priority"),
      channel: [],
      source: source ? [source] : [],
      starred: params.get("starred") === "true" ? true : null,
      text: params.get("text") ?? "",
      older_than_days: older ? Number(older) : null,
      newer_than_days: newer ? Number(newer) : null,
    });
    return {
      channels: this.taxonomy.channels.map((c) => ({ ...c, items: found.filter((i) => i.channel === c.name).length })),
    };
  }

  /** What a filter selects, as the server reads it. Time is the fake clock, 2026-10-24 09:00 UTC. */
  private matching(filter: Filter): Item[] {
    const now = Date.parse("2026-10-24T09:00:00Z");
    const day = 86_400_000;
    const text = filter.text.toLowerCase();
    const states = filter.state.length > 0 ? filter.state : ["new", "seen"];
    return this.items.filter((i) => {
      const age = now - Date.parse(i.published_at);
      return (
        states.includes(i.state) &&
        (filter.priority.length === 0 || filter.priority.includes(i.priority)) &&
        (filter.channel.length === 0 ||
          filter.channel.some((c) => i.channel === c || i.channel.startsWith(`${c} > `))) &&
        (filter.source.length === 0 || filter.source.some((s) => i.sources.includes(s))) &&
        (filter.starred === null || i.starred) &&
        (!text || `${i.title} ${i.author}`.toLowerCase().includes(text)) &&
        (filter.older_than_days === null || age > filter.older_than_days * day) &&
        (filter.newer_than_days === null || age <= filter.newer_than_days * day)
      );
    });
  }

  /** An action on everything a filter matches, like the server: a dry run only counts and samples. */
  private sweep(body: { action?: string; rating?: number; dry_run: boolean; filter: Filter }): Response {
    const matches = this.matching(body.filter);
    const state = { done: "done", open: "seen", snooze: "snoozed" }[body.action ?? ""] as Item["state"] | undefined;
    const undo = body.dry_run
      ? []
      : matches.map((i) => ({
          id: i.id,
          state: i.state,
          snoozed_until: i.snoozed_until,
          starred: i.starred,
          rating: i.rating,
        }));
    if (!body.dry_run) {
      for (const item of matches) {
        if (body.rating !== undefined) item.rating = body.rating;
        else if (state) item.state = state;
      }
    }
    return this.json({
      matched: matches.length,
      changed: body.dry_run ? 0 : matches.length,
      sample: matches.slice(0, 5),
      undo,
    });
  }

  /** Like the server: the same rating for all of them, set and never toggled; a missing item changes nothing. */
  private rateMany(body: { ids: string[]; rating: number }): Response {
    const found = body.ids.map((id) => this.items.find((i) => i.id === id));
    const missing = body.ids.find((_id, index) => !found[index]);
    if (missing !== undefined) return this.json({ detail: `no item ${missing}` }, 404);
    const undo = found.map((i) => {
      const item = i as Item;
      return {
        id: item.id,
        state: item.state,
        snoozed_until: item.snoozed_until,
        starred: item.starred,
        rating: item.rating,
      };
    });
    for (const item of found) (item as Item).rating = body.rating;
    return this.json({ changed: found.length, undo });
  }

  private restoreMany(body: { entries: { id: string; state: Item["state"]; rating?: number }[] }): Response {
    for (const entry of body.entries) {
      const item = this.items.find((i) => i.id === entry.id);
      if (item) Object.assign(item, { state: entry.state, rating: entry.rating ?? item.rating });
    }
    return this.json({ changed: body.entries.length });
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
        snooze: { state: "snoozed" as const, snoozed_until: "2026-10-25T09:00:00Z" },
        reopen: { state: "seen" as const },
        star: { starred: true },
        unstar: { starred: false },
      }[body.action] ?? {};
    Object.assign(item, next);
    this.undo.set(id, before);
    const result: ActionResult = {
      item,
      undo: {
        state: before.state,
        snoozed_until: before.snoozed_until,
        starred: before.starred,
        rating: before.rating,
      },
    };
    return this.json(result);
  }

  /** Like the server: a thumb sets the rating, the same thumb again clears it; the item stays where it is. */
  private rate(id: string, body: { rating: number }): Response {
    const item = this.items.find((i) => i.id === id);
    if (!item) return this.json({ detail: `no item ${id}` }, 404);
    const before = { state: item.state, snoozed_until: item.snoozed_until, starred: item.starred, rating: item.rating };
    item.rating = item.rating === body.rating ? 0 : body.rating;
    const result: ActionResult = { item, undo: before };
    return this.json(result);
  }

  private restore(id: string, back: Pick<Item, "state" | "snoozed_until" | "starred" | "rating">): Response {
    const item = this.items.find((i) => i.id === id) as Item;
    Object.assign(item, back);
    return this.json(item);
  }

  private bulk(body: { ids: string[]; action: string }): Response {
    const state = { done: "done", snooze: "snoozed" }[body.action] as Item["state"];
    for (const item of this.items) if (body.ids.includes(item.id)) item.state = state;
    return this.json({ changed: body.ids.length });
  }

  private seenBelow(): Response {
    const low = this.items.filter((i) => i.state === "new" && (i.priority === "P2" || i.priority === "P3"));
    for (const item of low) item.state = "seen";
    return this.json({ changed: low.length });
  }

  /** Like the server: a source may only feed categories that exist. */
  private addSource(body: Partial<Source>): Response {
    const unknown = (body.channels ?? []).find((c) => !this.taxonomy.channels.some((k) => k.name === c));
    if (unknown !== undefined) {
      return this.json({ detail: `source '${body.name}' feeds the channel '${unknown}', which does not exist` }, 422);
    }
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

  /** Like the server: a digest of nothing is refused, and one is kept when the model succeeds. */
  private makeDigest(body: { filter: { text: string } }): Response {
    if (this.digestFails) return this.json({ detail: this.digestFails }, 502);
    const chosen = this.items.filter((i) => i.title.toLowerCase().includes(body.filter.text.toLowerCase()));
    if (chosen.length === 0) return this.json({ detail: "nothing matches this selection" }, 422);
    const ref = (i: Item) => ({
      id: i.id,
      title: i.title,
      url: i.url,
      sources: i.sources,
      priority: i.priority,
      state: i.state,
    });
    const made: Digest = {
      id: `d${String(this.digests.length + 1)}`,
      created_at: "2026-10-24T09:00:00Z",
      scope: body.filter.text ? `matching '${body.filter.text}'` : "Inbox",
      headline: "Today: a security fix and a release.",
      sections: [
        { title: "Dev", points: chosen.slice(0, 2).map((i) => ({ text: `About ${i.title}.`, items: [ref(i)] })) },
      ],
      uncovered: chosen.slice(2).map(ref),
      cited: chosen.slice(0, 2).map((i) => i.id),
      count: chosen.length,
      total: chosen.length,
    };
    this.digests.unshift(made);
    return this.json(made, 201);
  }

  private oneDigest(method: string, id: string): Response {
    const index = this.digests.findIndex((d) => d.id === id);
    if (index < 0) return this.json({ detail: `no digest ${id}` }, 404);
    if (method === "DELETE") {
      this.digests.splice(index, 1);
      return new Response(null, { status: 204 });
    }
    const digest = this.digests[index] as Digest;
    // The state of the cited items is today's, not the day it was written.
    const state = (ref: Digest["uncovered"][number]) => ({
      ...ref,
      state: this.items.find((i) => i.id === ref.id)?.state ?? ref.state,
    });
    return this.json({
      ...digest,
      sections: digest.sections.map((s) => ({
        ...s,
        points: s.points.map((p) => ({ ...p, items: p.items.map(state) })),
      })),
      uncovered: digest.uncovered.map(state),
    });
  }

  private addChannel(body: Partial<Channel> & { name: string }): Response {
    this.taxonomy.channels.push({ description: "", ...body, icon: body.icon ?? "", items: 0, sources: [] });
    return this.json(body, 201);
  }

  /** Like the server: only categories that exist can be moved, or moved into. */
  private moveChannel(name: string, parent: string): Response {
    const known = (path: string) => this.taxonomy.channels.some((c) => c.name === path);
    const unknown = [name, parent].find((path) => path !== "" && !known(path));
    if (unknown !== undefined) return this.json({ detail: `no such source or channel: ${unknown}` }, 404);
    const target = parent ? `${parent} > ${name.split(" > ").pop() as string}` : (name.split(" > ").pop() as string);
    for (const channel of this.taxonomy.channels) {
      if (channel.name === name || channel.name.startsWith(`${name} > `))
        channel.name = target + channel.name.slice(name.length);
    }
    for (const item of this.items) {
      if (item.channel === name || item.channel.startsWith(`${name} > `))
        item.channel = target + item.channel.slice(name.length);
    }
    return this.json({ name: target, description: "", icon: "" });
  }

  private changeChannel(method: string, name: string, body: Partial<Channel>): Response {
    const index = this.taxonomy.channels.findIndex((c) => c.name === name);
    if (method === "DELETE") {
      this.taxonomy.channels.splice(index, 1);
      return new Response(null, { status: 204 });
    }
    const channel = this.taxonomy.channels[index] as Channel;
    // Like the server: an icon is one emoji, or empty.
    if (body.icon && /[\p{L}\p{N}<>]/u.test(body.icon)) return this.json({ detail: "an icon is one emoji" }, 422);
    Object.assign(channel, body);
    return this.json(channel);
  }
}
