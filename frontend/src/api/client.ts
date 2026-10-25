import type {
  Action,
  ActionResult,
  Channel,
  Digest,
  DigestJob,
  DigestSummary,
  Filters,
  IconResult,
  Item,
  ItemDetail,
  ItemPage,
  Rating,
  RefileResult,
  RunStatus,
  Source,
  SourceBody,
  SourceCreate,
  SourceType,
  Sweep,
  SweepChoice,
  BulkRating,
  Taxonomy,
  Undo,
  UndoEntry,
} from "./types";

/** An answer the backend refused, with the message it gave. */
export class ApiError extends Error {
  readonly status: number;

  constructor(status: number, message: string) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

async function call<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response;
  try {
    const headers = new Headers(init?.headers);
    headers.set("Content-Type", "application/json");
    response = await fetch(path, { ...init, headers });
  } catch {
    throw new ApiError(0, "Cannot reach Lookout. Is `lookout serve` running?");
  }
  if (!response.ok) {
    const body = (await response.json().catch(() => ({}))) as { detail?: unknown };
    const detail = typeof body.detail === "string" ? body.detail : `Request failed (${response.status})`;
    throw new ApiError(response.status, detail);
  }
  return response.status === 204 ? (undefined as T) : ((await response.json()) as T);
}

const STATES: Record<Filters["view"], string[]> = {
  inbox: [],
  snoozed: ["snoozed"],
  done: ["done"],
  expired: ["expired"],
  all: ["new", "seen", "snoozed", "done", "expired"],
};

/** Items are loaded this many at a time. */
export const PAGE = 50;

const DAYS: Record<Exclude<Filters["age"], "">, { key: "older_than_days" | "newer_than_days"; days: number }> = {
  older7: { key: "older_than_days", days: 7 },
  older14: { key: "older_than_days", days: 14 },
  older30: { key: "older_than_days", days: 30 },
  newer7: { key: "newer_than_days", days: 7 },
};

/** What the filters select, as query parameters; the list and the category counts must read it the same way. */
function selection(filters: Filters, { withCategory }: { withCategory: boolean }): URLSearchParams {
  const params = new URLSearchParams();
  for (const priority of filters.priorities) params.append("priority", priority);
  if (withCategory && filters.channel) params.set("channel", filters.channel);
  if (filters.source) params.set("source", filters.source);
  for (const state of STATES[filters.view]) params.append("state", state);
  if (filters.starred) params.set("starred", "true");
  if (filters.text) params.set("text", filters.text);
  if (filters.age) params.set(DAYS[filters.age].key, String(DAYS[filters.age].days));
  return params;
}

/** The categories with how many items these filters would list in each (the category itself aside). */
export const taxonomyQuery = (filters: Filters): string => selection(filters, { withCategory: false }).toString();

export function itemsQuery(filters: Filters, limit = PAGE, offset = 0): string {
  const params = selection(filters, { withCategory: true });
  if (filters.order !== "priority") params.set("order", filters.order);
  params.set("limit", String(limit));
  if (offset > 0) params.set("offset", String(offset));
  return params.toString();
}

/** The same selection as a body for an action on everything it matches. */
export function filterBody(filters: Filters) {
  const age = filters.age ? DAYS[filters.age] : null;
  return {
    priority: filters.priorities,
    channel: filters.channel ? [filters.channel] : [],
    source: filters.source ? [filters.source] : [],
    state: STATES[filters.view],
    starred: filters.starred ? true : null,
    text: filters.text,
    older_than_days: age?.key === "older_than_days" ? age.days : null,
    newer_than_days: age?.key === "newer_than_days" ? age.days : null,
  };
}

export const api = {
  items: (filters: Filters, offset = 0) => call<ItemPage>(`/api/items?${itemsQuery(filters, PAGE, offset)}`),
  item: (id: string) => call<ItemDetail>(`/api/items/${id}`),
  act: (id: string, action: Action, hours?: number) =>
    call<ActionResult>(`/api/items/${id}/actions`, { method: "POST", body: JSON.stringify({ action, hours }) }),
  rate: (id: string, rating: Rating) =>
    call<ActionResult>(`/api/items/${id}/rating`, { method: "POST", body: JSON.stringify({ rating }) }),
  restore: (id: string, undo: Undo) =>
    call<Item>(`/api/items/${id}/restore`, { method: "POST", body: JSON.stringify(undo) }),
  bulk: (ids: string[], action: Action, hours?: number) =>
    call<{ changed: number }>("/api/items/bulk", { method: "POST", body: JSON.stringify({ ids, action, hours }) }),
  seenBelow: (priority: string) =>
    call<{ changed: number }>("/api/items/seen-below", { method: "POST", body: JSON.stringify({ priority }) }),
  sweep: (filters: Filters, choice: SweepChoice, dryRun: boolean) =>
    call<Sweep>("/api/items/sweep", {
      method: "POST",
      body: JSON.stringify({ ...choice, dry_run: dryRun, filter: filterBody(filters) }),
    }),
  rateMany: (ids: string[], rating: Rating) =>
    call<BulkRating>("/api/items/bulk-rating", { method: "POST", body: JSON.stringify({ ids, rating }) }),
  restoreMany: (entries: UndoEntry[]) =>
    call<{ changed: number }>("/api/items/restore-many", { method: "POST", body: JSON.stringify({ entries }) }),
  taxonomy: (filters: Filters) => call<Taxonomy>(`/api/taxonomy?${taxonomyQuery(filters)}`),
  sourceTypes: () => call<SourceType[]>("/api/source-types"),
  addSource: (source: SourceCreate) => call<Source>("/api/sources", { method: "POST", body: JSON.stringify(source) }),
  updateSource: (name: string, source: SourceBody) =>
    call<Source>(`/api/sources/${encodeURIComponent(name)}`, { method: "PUT", body: JSON.stringify(source) }),
  deleteSource: (name: string) => call<undefined>(`/api/sources/${encodeURIComponent(name)}`, { method: "DELETE" }),
  addChannel: (name: string, description: string) =>
    call<Channel>("/api/channels", { method: "POST", body: JSON.stringify({ name, description }) }),
  updateChannel: (name: string, change: { description?: string; icon?: string }) =>
    call<Channel>(`/api/channels/${encodeURIComponent(name)}`, {
      method: "PATCH",
      body: JSON.stringify(change),
    }),
  digests: () => call<DigestSummary[]>("/api/digests"),
  digest: (id: string) => call<Digest>(`/api/digests/${encodeURIComponent(id)}`),
  startDigest: (filters: Filters) =>
    call<DigestJob>("/api/digests", { method: "POST", body: JSON.stringify({ filter: filterBody(filters) }) }),
  digestJobs: () => call<DigestJob[]>("/api/digests/jobs"),
  cancelDigestJob: (id: string) =>
    call<DigestJob>(`/api/digests/jobs/${encodeURIComponent(id)}/cancel`, { method: "POST" }),
  dismissDigestJob: (id: string) =>
    call<undefined>(`/api/digests/jobs/${encodeURIComponent(id)}`, { method: "DELETE" }),
  deleteDigest: (id: string) => call<undefined>(`/api/digests/${encodeURIComponent(id)}`, { method: "DELETE" }),
  suggestIcons: () => call<IconResult>("/api/channels/icons", { method: "POST" }),
  refile: (dryRun = false) => call<RefileResult>(`/api/refile?dry_run=${String(dryRun)}`, { method: "POST" }),
  moveChannel: (name: string, parent: string) =>
    call<Channel>(`/api/channels/${encodeURIComponent(name)}/move`, {
      method: "POST",
      body: JSON.stringify({ parent }),
    }),
  deleteChannel: (name: string) => call<undefined>(`/api/channels/${encodeURIComponent(name)}`, { method: "DELETE" }),
  sources: () => call<Source[]>("/api/sources"),
  setSource: (name: string, enabled: boolean) =>
    call<Source>(`/api/sources/${encodeURIComponent(name)}`, { method: "PATCH", body: JSON.stringify({ enabled }) }),
  runStatus: () => call<RunStatus>("/api/run"),
  run: () => call<RunStatus>("/api/run", { method: "POST" }),
};
