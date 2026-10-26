import { useCallback, useEffect, useMemo, useState } from "react";
import type { CSSProperties, MouseEvent } from "react";
import { createPortal } from "react-dom";
import type { Action, Filters, Item, Rating, Sweep } from "../api/types";
import {
  useAct,
  useBulk,
  useDigestJobs,
  useStartDigest,
  useItems,
  useRate,
  useRateMany,
  useRestore,
  useRestoreMany,
  useSeenBelow,
  useSources,
  useTaxonomy,
} from "../hooks";
import { readLastVisit, rememberVisit } from "../lastVisit";
import { readListWidth, rememberListWidth } from "../listWidth";
import { inboxTotal } from "../categories";
import { useShortcuts } from "../shortcuts";
import { CategoryTree } from "./CategoryTree";
import { ColumnResizer } from "./ColumnResizer";
import { FilterBar, OrderToggle, VIEWS } from "./FilterBar";
import { ItemDetail } from "./ItemDetail";
import { ItemList } from "./ItemList";
import { HelpDialog, SnoozeMenu, Toast } from "./Overlays";
import { RunStrip } from "./RunStrip";
import { StateView } from "./StateView";
import { SweepDialog } from "./SweepDialog";

const DONE_TEXT: Record<Action, string> = {
  open: "Opened",
  done: "Marked done",
  snooze: "Snoozed",
  reopen: "Reopened",
  star: "Starred",
  unstar: "Unstarred",
};

/** Closes the menu a button sits in, then does what the button is for. */
const closing = (action: () => void) => (event: MouseEvent<HTMLElement>) => {
  (event.currentTarget.closest("details") as HTMLDetailsElement).open = false;
  action();
};

const errorText = (error: unknown): string => (error as Error).message;

interface Props {
  /** Where the category tree goes: the sidebar, once it is mounted. */
  side: HTMLElement | null;
  filters: Filters;
  openId: string | null;
  onFilters: (filters: Filters) => void;
  /** Show an item in the panel, or close it. ``replace`` previews without adding to the browser history. */
  onOpen: (id: string | null, replace?: boolean) => void;
}

interface Message {
  text: string;
  undo?: () => void;
}

export function Inbox({ side, filters, openId, onFilters, onOpen }: Props) {
  const items = useItems(filters);
  const sources = useSources();
  const taxonomy = useTaxonomy(filters);
  const act = useAct();
  const bulk = useBulk();
  const startDigest = useStartDigest();
  const jobs = useDigestJobs();
  const writing = jobs.data?.some((j) => j.state === "running") ?? false;
  const restore = useRestore();
  const restoreMany = useRestoreMany();
  const rate = useRate();
  const rateMany = useRateMany();
  const seenBelow = useSeenBelow();
  const [focusedId, setFocusedId] = useState<string | null>(null);
  const [picked, setSelected] = useState<ReadonlySet<string>>(new Set());
  const [snoozing, setSnoozing] = useState<string[] | null>(null);
  const [help, setHelp] = useState(false);
  const [listWidth, setListWidth] = useState(readListWidth);
  const [message, setMessage] = useState<Message | null>(null);
  const [sweeping, setSweeping] = useState(false);
  const [lastVisit] = useState(readLastVisit);
  useEffect(() => {
    const remember = () => {
      rememberVisit(new Date());
    };
    window.addEventListener("pagehide", remember);
    return () => {
      window.removeEventListener("pagehide", remember);
      remember();
    };
  }, []);

  const list = useMemo(() => items.data?.pages.flatMap((page) => page.items) ?? [], [items.data]);
  const total = items.data?.pages.at(-1)?.total ?? 0;
  const earlierFrom = useMemo(() => {
    if (filters.order !== "date" || lastVisit === null) return null;
    const first = list.findIndex((i) => new Date(i.published_at) < lastVisit);
    return first > 0 ? (list[first] as Item).id : null;
  }, [filters.order, lastVisit, list]);
  const sourceNames = useMemo(
    () =>
      [...new Set([...(sources.data ?? []).map((s) => s.name), ...(filters.source ? [filters.source] : [])])].sort(),
    [sources.data, filters.source],
  );
  const focused = list.find((i) => i.id === focusedId) ?? list[0];
  /** The panel always shows an item: the one opened, else the one the list is on (a preview, which reads nothing). */
  const shownId = openId ?? focused?.id ?? null;
  const urgent = useMemo(() => list.filter((i) => i.priority === "P0"), [list]);

  // Items that left the list (done, filtered out) are no longer selected.
  const selected = useMemo(() => new Set([...picked].filter((id) => list.some((i) => i.id === id))), [picked, list]);

  const targets = useCallback((): string[] => {
    if (selected.size > 0) return [...selected];
    return focused ? [focused.id] : [];
  }, [selected, focused]);

  /** After clearing items: focus the next item still there, and if the panel showed a cleared one, show it there. */
  const moveOn = useCallback(
    (ids: string[]) => {
      const gone = new Set(ids);
      const first = list.findIndex((i) => gone.has(i.id));
      const after = list.slice(first + 1).find((i) => !gone.has(i.id));
      const before = list.slice(0, Math.max(first, 0)).findLast((i) => !gone.has(i.id));
      const next = (after ?? before)?.id ?? null;
      setFocusedId(next);
      if (openId && gone.has(openId)) onOpen(next, true);
    },
    [list, openId, onOpen],
  );

  const rateItem = useCallback(
    async (id: string, rating: Exclude<Rating, 0>) => {
      try {
        const result = await rate.mutateAsync({ id, rating });
        const now = result.item.rating;
        setMessage({
          text: now === 1 ? "More like this" : now === -1 ? "Less like this" : "Rating cleared",
          undo: () => {
            restore.mutateAsync({ id, undo: result.undo }).then(
              () => {
                setMessage(null);
              },
              (error: unknown) => {
                setMessage({ text: errorText(error) });
              },
            );
          },
        });
      } catch (error) {
        setMessage({ text: errorText(error) });
      }
    },
    [rate, restore],
  );

  const perform = useCallback(
    async (action: Action, ids: string[], hours?: number) => {
      try {
        if (ids.length === 1) {
          const id = ids[0] as string;
          const result = await act.mutateAsync({ id, action, hours });
          if (action === "done") moveOn(ids);
          setMessage({
            text: DONE_TEXT[action],
            undo: () => {
              restore.mutateAsync({ id, undo: result.undo }).then(
                () => {
                  setMessage(null);
                },
                (error: unknown) => {
                  setMessage({ text: errorText(error) });
                },
              );
            },
          });
        } else {
          const result = await bulk.mutateAsync({ ids, action, hours });
          if (action === "done") moveOn(ids);
          setSelected(new Set());
          setMessage({ text: `${DONE_TEXT[action]}: ${result.changed} items` });
        }
      } catch (error) {
        setMessage({ text: errorText(error) });
      }
    },
    [act, bulk, restore, moveOn],
  );

  /** Rate everything selected: the same rating for all, never toggled. */
  const rateSelection = useCallback(
    async (ids: string[], rating: Exclude<Rating, 0>) => {
      try {
        const result = await rateMany.mutateAsync({ ids, rating });
        setMessage({
          text: `${rating === 1 ? "More like this" : "Less like this"}: ${result.changed} items`,
          undo: () => {
            restoreMany.mutateAsync(result.undo).then(
              () => {
                setMessage(null);
              },
              (error: unknown) => {
                setMessage({ text: errorText(error) });
              },
            );
          },
        });
      } catch (error) {
        setMessage({ text: errorText(error) });
      }
    },
    [rateMany, restoreMany],
  );

  /** A thumb key: on the selection when there is one, else on the focused item (where the same thumb clears). */
  const thumb = useCallback(
    (rating: Exclude<Rating, 0>) => {
      if (selected.size > 0) void rateSelection([...selected], rating);
      else if (focused) void rateItem(focused.id, rating);
    },
    [selected, focused, rateSelection, rateItem],
  );

  const swept = useCallback(
    (result: Sweep, said: string) => {
      setSweeping(false);
      setSelected(new Set());
      setMessage({
        text: `${said}: ${result.changed} items`,
        undo: () => {
          restoreMany.mutateAsync(result.undo).then(
            () => {
              setMessage(null);
            },
            (error: unknown) => {
              setMessage({ text: errorText(error) });
            },
          );
        },
      });
    },
    [restoreMany],
  );

  const move = useCallback(
    (step: number) => {
      if (list.length === 0) return;
      const index = Math.max(
        0,
        list.findIndex((i) => i.id === focused?.id),
      );
      // The panel follows the focus, like the preview pane of a mail client. Only an explicit open (o, Enter, a click)
      // marks the item seen and counts as having read it, so skimming past items teaches nothing.
      const next = (list[Math.min(list.length - 1, Math.max(0, index + step))] as Item).id;
      setFocusedId(next);
      onOpen(next, true);
    },
    [list, focused, onOpen],
  );

  const open = useCallback(
    (id: string) => {
      setFocusedId(id);
      onOpen(id);
      if (list.find((i) => i.id === id)?.state === "new") act.mutate({ id, action: "open" });
    },
    [act, list, onOpen],
  );

  const toggle = useCallback((id: string) => {
    setSelected((current) => {
      const next = new Set(current);
      if (!next.delete(id)) next.add(id);
      return next;
    });
  }, []);

  const handlers = useMemo(
    () => ({
      j: () => {
        move(1);
      },
      k: () => {
        move(-1);
      },
      o: () => {
        if (focused) open(focused.id);
      },
      Enter: () => {
        if (focused) open(focused.id);
      },
      e: () => {
        void perform("done", targets());
      },
      "+": () => {
        thumb(1);
      },
      "=": () => {
        thumb(1);
      },
      "-": () => {
        thumb(-1);
      },
      s: () => {
        const ids = targets();
        if (ids.length > 0) setSnoozing(ids);
      },
      "*": () => {
        if (focused) void perform(focused.starred ? "unstar" : "star", [focused.id]);
      },
      x: () => {
        if (focused) toggle(focused.id);
      },
      u: () => {
        message?.undo?.();
      },
      "?": () => {
        setHelp(true);
      },
    }),
    [move, open, perform, thumb, targets, toggle, focused, message],
  );
  const overlay = snoozing !== null || help;
  useShortcuts(handlers, !overlay);
  useShortcuts(
    useMemo(
      () => ({
        Escape: () => {
          setSnoozing(null);
          setHelp(false);
        },
      }),
      [],
    ),
    overlay,
  );
  const dismissMessage = useCallback(() => {
    setMessage(null);
  }, []);

  let content;
  if (items.isPending) content = <StateView kind="loading" />;
  else if (items.isError)
    content = <StateView kind="error" message={items.error.message} onRetry={() => void items.refetch()} />;
  else if (list.length === 0) {
    content = (
      <StateView kind="empty" message="Nothing to look at. Lookout fetches on its schedule, or press Run now." />
    );
  } else {
    content = (
      <ItemList
        items={list}
        focusedId={(focused as Item).id}
        selected={selected}
        now={new Date()}
        earlierFrom={earlierFrom}
        onFocus={setFocusedId}
        onOpen={open}
        onToggle={toggle}
        onRate={(id, rating) => {
          void rateItem(id, rating);
        }}
        onDone={(id) => {
          void perform("done", [id]);
        }}
      />
    );
  }

  return (
    <div className="inbox">
      {side &&
        taxonomy.data &&
        createPortal(
          <CategoryTree
            channels={taxonomy.data.channels}
            selected={filters.channel}
            onSelect={(path) => {
              onFilters({ ...filters, channel: path });
            }}
          />,
          side,
        )}
      <div className="inbox-main">
        <div className="titlerow">
          <div>
            <h1>Inbox</h1>
            {urgent.length > 0 && (
              <p className="finding">
                <strong>
                  {urgent.length} {urgent.length === 1 ? "needs" : "need"} action today:
                </strong>{" "}
                {(urgent[0] as Item).title}
              </p>
            )}
          </div>
          <RunStrip />
        </div>
        <div className="columns" style={{ "--list-w": `${String(listWidth)}px` } as CSSProperties}>
          <section className="listcol" aria-label="Inbox">
            <FilterBar
              filters={filters}
              sources={sourceNames}
              inboxCount={taxonomy.data && inboxTotal(taxonomy.data.channels)}
              onChange={onFilters}
            />
            {filters.text && filters.view !== "all" && (
              <p className="nudge" role="note">
                Searching only <strong>{VIEWS.find((v) => v.value === filters.view)?.label}</strong>. Done, snoozed and
                expired items, and older ones, are not looked at.{" "}
                <button
                  type="button"
                  onClick={() => {
                    onFilters({ ...filters, view: "all", age: "" });
                  }}
                >
                  Search everything
                </button>
              </p>
            )}
            {list.length > 0 && list.every((i) => i.channel === "Other") && (
              <p className="nudge" role="note">
                Everything here is in <strong>Other</strong>. <a href="/categories">Define categories</a> (AI, Dev &gt;
                Rust, ...) so Lookout can file your items.
              </p>
            )}
            <div className="toolbar">
              <span>{items.data ? `${list.length} of ${total}` : ""}</span>
              <OrderToggle filters={filters} onChange={onFilters} />
              <details className="menu">
                <summary>Actions</summary>
                <div>
                  {total > 0 && (
                    <button
                      type="button"
                      onClick={closing(() => {
                        setSweeping(true);
                      })}
                    >
                      Act on all {total}…
                    </button>
                  )}
                  {total > 0 && (
                    <button
                      type="button"
                      disabled={writing || startDigest.isPending}
                      title={writing ? "A digest is already being written: follow it under Digest." : undefined}
                      onClick={closing(() => {
                        startDigest.mutate(filters, {
                          onSuccess: () => {
                            setMessage({ text: "Writing the digest in the background: it will appear under Digest." });
                          },
                          onError: (error) => {
                            setMessage({ text: errorText(error) });
                          },
                        });
                      })}
                    >
                      Summarise these {total}…
                    </button>
                  )}
                  <button
                    type="button"
                    onClick={closing(() => {
                      seenBelow.mutate("P1");
                    })}
                  >
                    Mark P2 and P3 as seen
                  </button>
                  <button
                    type="button"
                    onClick={closing(() => {
                      setHelp(true);
                    })}
                  >
                    Shortcuts
                  </button>
                </div>
              </details>
            </div>
            {selected.size > 0 && (
              <div className="bulk" role="group" aria-label="Bulk actions">
                <span>{selected.size} selected</span>
                <button
                  type="button"
                  onClick={() => {
                    void perform("done", [...selected]);
                  }}
                >
                  Done
                </button>
                <button
                  type="button"
                  onClick={() => {
                    setSnoozing([...selected]);
                  }}
                >
                  Snooze…
                </button>
                <button
                  type="button"
                  onClick={() => {
                    void rateSelection([...selected], 1);
                  }}
                >
                  More like this
                </button>
                <button
                  type="button"
                  onClick={() => {
                    void rateSelection([...selected], -1);
                  }}
                >
                  Less like this
                </button>
                <button
                  type="button"
                  onClick={() => {
                    setSelected(new Set());
                  }}
                >
                  Clear
                </button>
              </div>
            )}
            <div className="list">
              {content}
              {items.hasNextPage && (
                <p className="more">
                  <button
                    type="button"
                    disabled={items.isFetchingNextPage}
                    onClick={() => {
                      void items.fetchNextPage();
                    }}
                  >
                    Load more ({list.length} of {total})
                  </button>
                </p>
              )}
            </div>
          </section>
          {shownId && (
            <ColumnResizer
              width={listWidth}
              onChange={(width) => {
                setListWidth(width);
                rememberListWidth(width);
              }}
            />
          )}
          {shownId && (
            <ItemDetail
              key={shownId}
              id={shownId}
              onAction={(action) => {
                void perform(action, [shownId]);
              }}
              onRate={(rating) => {
                void rateItem(shownId, rating);
              }}
              onSnooze={() => {
                setSnoozing([shownId]);
              }}
              onClose={() => {
                onOpen(null);
              }}
            />
          )}
        </div>
        {sweeping && (
          <SweepDialog
            filters={filters}
            onClose={() => {
              setSweeping(false);
            }}
            onDone={swept}
          />
        )}
        {snoozing && (
          <SnoozeMenu
            onPick={(hours) => {
              void perform("snooze", snoozing, hours);
              setSnoozing(null);
            }}
            onClose={() => {
              setSnoozing(null);
            }}
          />
        )}
        {help && (
          <HelpDialog
            onClose={() => {
              setHelp(false);
            }}
          />
        )}
        {message && <Toast message={message.text} onUndo={message.undo} onDismiss={dismissMessage} />}
      </div>
    </div>
  );
}
