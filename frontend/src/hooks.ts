import { useEffect } from "react";
import { useInfiniteQuery, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api, taxonomyQuery } from "./api/client";
import { NO_FILTERS } from "./api/types";
import type { Action, Filters, Rating, SourceBody, SweepChoice, UndoEntry } from "./api/types";

/** The items of a selection, a page at a time: the next page starts after what is already loaded. */
export const useItems = (filters: Filters) =>
  useInfiniteQuery({
    queryKey: ["items", filters],
    queryFn: ({ pageParam }) => api.items(filters, pageParam),
    initialPageParam: 0,
    getNextPageParam: (last, pages) => {
      const loaded = pages.reduce((sum, page) => sum + page.items.length, 0);
      return loaded < last.total ? loaded : undefined;
    },
  });

export const useItem = (id: string | null) =>
  useQuery({ queryKey: ["item", id], queryFn: () => api.item(id as string), enabled: id !== null });

/** The categories, counted for the same filters as the list beside them (none: what is in the inbox). */
export const useTaxonomy = (filters: Filters = NO_FILTERS) =>
  useQuery({
    queryKey: ["taxonomy", taxonomyQuery(filters)],
    queryFn: () => api.taxonomy(filters),
    staleTime: 60_000,
  });

export const useDigests = () => useQuery({ queryKey: ["digests"], queryFn: api.digests });

/** One digest; an empty id (the list page) asks for nothing. */
export const useDigest = (id: string) =>
  useQuery({ queryKey: ["digest", id], queryFn: () => api.digest(id), enabled: id !== "" });

/** How often a digest being written is asked after. */
export const JOB_POLL_MS = 1000;

/** The digests being written or lately finished. They are asked after only while one is being written. */
export function useDigestJobs() {
  const client = useQueryClient();
  const query = useQuery({
    queryKey: ["digest-jobs"],
    queryFn: api.digestJobs,
    refetchInterval: (q) => (q.state.data?.some((j) => j.state === "running") ? JOB_POLL_MS : false),
  });
  // A digest that has just been written joins the kept ones.
  const done = query.data?.filter((j) => j.state === "done").length ?? 0;
  useEffect(() => {
    void client.invalidateQueries({ queryKey: ["digests"] });
  }, [done, client]);
  return query;
}

/** Ask for a digest of a selection; it is written in the background. */
export function useStartDigest() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: api.startDigest,
    onSuccess: () => client.invalidateQueries({ queryKey: ["digest-jobs"] }),
  });
}

export function useCancelDigestJob() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: api.cancelDigestJob,
    onSuccess: () => client.invalidateQueries({ queryKey: ["digest-jobs"] }),
  });
}

export function useDismissDigestJob() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: api.dismissDigestJob,
    onSuccess: () => client.invalidateQueries({ queryKey: ["digest-jobs"] }),
  });
}

/** Delete a digest. ``onDeleted`` runs first, to leave the page before anything tries to load the digest again. */
export function useDeleteDigest(onDeleted: () => void) {
  const refresh = useRefresh();
  return useMutation({
    mutationFn: api.deleteDigest,
    onSuccess: () => {
      onDeleted();
      return refresh();
    },
  });
}

export const useSourceTypes = () =>
  useQuery({ queryKey: ["source-types"], queryFn: api.sourceTypes, staleTime: Infinity });

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

/** An action on everything a selection matches; a dry run only counts. */
export function useSweep() {
  const refresh = useRefresh();
  return useMutation({
    mutationFn: ({ filters, choice, dryRun }: { filters: Filters; choice: SweepChoice; dryRun: boolean }) =>
      api.sweep(filters, choice, dryRun),
    onSuccess: (_result, { dryRun }) => (dryRun ? undefined : refresh()),
  });
}

export function useRestoreMany() {
  const refresh = useRefresh();
  return useMutation({ mutationFn: (entries: UndoEntry[]) => api.restoreMany(entries), onSuccess: refresh });
}

/** Give several items one rating (set, never toggled). */
export function useRateMany() {
  const refresh = useRefresh();
  return useMutation({
    mutationFn: ({ ids, rating }: { ids: string[]; rating: Rating }) => api.rateMany(ids, rating),
    onSuccess: refresh,
  });
}

/** Thumbs up or down; the same thumb again clears it. */
export function useRate() {
  const refresh = useRefresh();
  return useMutation({
    mutationFn: ({ id, rating }: { id: string; rating: Rating }) => api.rate(id, rating),
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

/** The management actions of sources and channels: each refreshes everything on screen, taxonomy included. */
export function useManage() {
  const refresh = useRefresh();
  const options = { onSuccess: refresh };
  return {
    addSource: useMutation({ mutationFn: api.addSource, ...options }),
    updateSource: useMutation({
      mutationFn: ({ name, body }: { name: string; body: SourceBody }) => api.updateSource(name, body),
      ...options,
    }),
    deleteSource: useMutation({ mutationFn: api.deleteSource, ...options }),
    addChannel: useMutation({
      mutationFn: ({ name, description }: { name: string; description: string }) => api.addChannel(name, description),
      ...options,
    }),
    updateChannel: useMutation({
      mutationFn: ({ name, ...change }: { name: string; description?: string; icon?: string }) =>
        api.updateChannel(name, change),
      ...options,
    }),
    suggestIcons: useMutation({ mutationFn: api.suggestIcons, ...options }),
    moveChannel: useMutation({
      mutationFn: ({ name, parent }: { name: string; parent: string }) => api.moveChannel(name, parent),
      ...options,
    }),
    deleteChannel: useMutation({ mutationFn: api.deleteChannel, ...options }),
    refile: useMutation({ mutationFn: () => api.refile(false), ...options }),
    previewRefile: useMutation({ mutationFn: () => api.refile(true) }),
  };
}
