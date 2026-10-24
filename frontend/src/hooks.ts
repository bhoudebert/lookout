import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "./api/client";
import type { Action, Filters } from "./api/types";

export const useItems = (filters: Filters) =>
  useQuery({ queryKey: ["items", filters], queryFn: () => api.items(filters) });

export const useItem = (id: string | null) =>
  useQuery({ queryKey: ["item", id], queryFn: () => api.item(id as string), enabled: id !== null });

export const useTaxonomy = () => useQuery({ queryKey: ["taxonomy"], queryFn: api.taxonomy, staleTime: 60_000 });

export const useSources = () => useQuery({ queryKey: ["sources"], queryFn: api.sources });

export const useRunStatus = () =>
  useQuery({
    queryKey: ["run"],
    queryFn: api.runStatus,
    refetchInterval: (query) => (query.state.data?.running ? 1000 : false),
  });

/** Anything that changes items or sources invalidates what is on screen. */
export function useRefresh(): () => Promise<void> {
  const client = useQueryClient();
  return () => client.invalidateQueries();
}

export function useAct() {
  const refresh = useRefresh();
  return useMutation({
    mutationFn: ({ id, action, hours }: { id: string; action: Action; hours?: number }) => api.act(id, action, hours),
    onSuccess: refresh,
  });
}

export function useBulk() {
  const refresh = useRefresh();
  return useMutation({
    mutationFn: ({ ids, action, hours }: { ids: string[]; action: Action; hours?: number }) =>
      api.bulk(ids, action, hours),
    onSuccess: refresh,
  });
}

export function useRestore() {
  const refresh = useRefresh();
  return useMutation({
    mutationFn: ({ id, undo }: { id: string; undo: Parameters<typeof api.restore>[1] }) => api.restore(id, undo),
    onSuccess: refresh,
  });
}

export function useSeenBelow() {
  const refresh = useRefresh();
  return useMutation({ mutationFn: (priority: string) => api.seenBelow(priority), onSuccess: refresh });
}

export function useSetSource() {
  const refresh = useRefresh();
  return useMutation({
    mutationFn: ({ name, enabled }: { name: string; enabled: boolean }) => api.setSource(name, enabled),
    onSuccess: refresh,
  });
}

export function useStartRun() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: api.run,
    onSuccess: (status) => {
      client.setQueryData(["run"], status);
    },
  });
}
