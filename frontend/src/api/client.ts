import type {
  Action,
  ActionResult,
  Channel,
  Filters,
  Item,
  ItemDetail,
  ItemPage,
  RunStatus,
  Source,
  SourceBody,
  SourceCreate,
  SourceType,
  Taxonomy,
  Undo,
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
  dismissed: ["dismissed"],
  all: ["new", "seen", "snoozed", "done", "dismissed"],
};

export function itemsQuery(filters: Filters, limit = 100): string {
  const params = new URLSearchParams();
  for (const priority of filters.priorities) params.append("priority", priority);
  if (filters.channel) params.set("channel", filters.channel);
  if (filters.kind) params.set("kind", filters.kind);
  if (filters.source) params.set("source", filters.source);
  for (const state of STATES[filters.view]) params.append("state", state);
  if (filters.starred) params.set("starred", "true");
  if (filters.text) params.set("text", filters.text);
  params.set("limit", String(limit));
  return params.toString();
}

export const api = {
  items: (filters: Filters) => call<ItemPage>(`/api/items?${itemsQuery(filters)}`),
  item: (id: string) => call<ItemDetail>(`/api/items/${id}`),
  act: (id: string, action: Action, hours?: number) =>
    call<ActionResult>(`/api/items/${id}/actions`, { method: "POST", body: JSON.stringify({ action, hours }) }),
  restore: (id: string, undo: Undo) =>
    call<Item>(`/api/items/${id}/restore`, { method: "POST", body: JSON.stringify(undo) }),
  bulk: (ids: string[], action: Action, hours?: number) =>
    call<{ changed: number }>("/api/items/bulk", { method: "POST", body: JSON.stringify({ ids, action, hours }) }),
  seenBelow: (priority: string) =>
    call<{ changed: number }>("/api/items/seen-below", { method: "POST", body: JSON.stringify({ priority }) }),
  taxonomy: () => call<Taxonomy>("/api/taxonomy"),
  sourceTypes: () => call<SourceType[]>("/api/source-types"),
  addSource: (source: SourceCreate) => call<Source>("/api/sources", { method: "POST", body: JSON.stringify(source) }),
  updateSource: (name: string, source: SourceBody) =>
    call<Source>(`/api/sources/${encodeURIComponent(name)}`, { method: "PUT", body: JSON.stringify(source) }),
  deleteSource: (name: string) => call<undefined>(`/api/sources/${encodeURIComponent(name)}`, { method: "DELETE" }),
  addChannel: (name: string, description: string) =>
    call<Channel>("/api/channels", { method: "POST", body: JSON.stringify({ name, description }) }),
  updateChannel: (name: string, description: string) =>
    call<Channel>(`/api/channels/${encodeURIComponent(name)}`, {
      method: "PATCH",
      body: JSON.stringify({ description }),
    }),
  deleteChannel: (name: string) => call<undefined>(`/api/channels/${encodeURIComponent(name)}`, { method: "DELETE" }),
  sources: () => call<Source[]>("/api/sources"),
  setSource: (name: string, enabled: boolean) =>
    call<Source>(`/api/sources/${encodeURIComponent(name)}`, { method: "PATCH", body: JSON.stringify({ enabled }) }),
  runStatus: () => call<RunStatus>("/api/run"),
  run: () => call<RunStatus>("/api/run", { method: "POST" }),
};
