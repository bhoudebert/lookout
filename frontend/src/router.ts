import { useCallback, useSyncExternalStore } from "react";
import { NO_FILTERS, PRIORITIES } from "./api/types";
import type { Age, Filters, Order, Priority, View } from "./api/types";

const VIEWS: readonly View[] = ["inbox", "snoozed", "done", "expired", "all"];
const AGES: readonly Age[] = ["older7", "older14", "older30", "newer7"];

export interface Location {
  path: string;
  filters: Filters;
  item: string | null;
}

export function parseLocation(path: string, search: string): Location {
  const params = new URLSearchParams(search);
  const view = params.get("view") as View | null;
  const age = params.get("age") as Age | null;
  const order = params.get("order") as Order | null;
  return {
    path,
    filters: {
      priorities: params.getAll("priority").filter((p): p is Priority => PRIORITIES.includes(p as Priority)),
      channel: params.get("category") ?? "",
      source: params.get("source") ?? "",
      view: view && VIEWS.includes(view) ? view : NO_FILTERS.view,
      starred: params.get("starred") === "true",
      text: params.get("q") ?? "",
      order: order === "date" ? "date" : NO_FILTERS.order,
      age: age && AGES.includes(age) ? age : NO_FILTERS.age,
    },
    item: params.get("item"),
  };
}

export function buildSearch(filters: Filters, item: string | null): string {
  const params = new URLSearchParams();
  for (const priority of filters.priorities) params.append("priority", priority);
  if (filters.channel) params.set("category", filters.channel);
  if (filters.source) params.set("source", filters.source);
  if (filters.view !== NO_FILTERS.view) params.set("view", filters.view);
  if (filters.starred) params.set("starred", "true");
  if (filters.text) params.set("q", filters.text);
  if (filters.order !== NO_FILTERS.order) params.set("order", filters.order);
  if (filters.age) params.set("age", filters.age);
  if (item) params.set("item", item);
  const text = params.toString();
  return text ? `?${text}` : "";
}

function subscribe(listener: () => void): () => void {
  window.addEventListener("popstate", listener);
  return () => {
    window.removeEventListener("popstate", listener);
  };
}

const snapshot = (): string => window.location.pathname + window.location.search;

/** The current location, kept in the URL so a filtered inbox can be bookmarked and shared. */
export function useLocation(): {
  location: Location;
  go: (path: string, filters?: Filters, item?: string | null) => void;
} {
  const raw = useSyncExternalStore(subscribe, snapshot);
  const [path = "/", search = ""] = raw.split(/(?=\?)/);
  const go = useCallback((to: string, filters: Filters = NO_FILTERS, item: string | null = null) => {
    window.history.pushState(null, "", to + buildSearch(filters, item));
    window.dispatchEvent(new PopStateEvent("popstate"));
  }, []);
  return { location: parseLocation(path, search), go };
}
