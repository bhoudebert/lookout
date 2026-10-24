import { useCallback, useMemo, useState } from "react";
import type { Action, Filters, Item } from "../api/types";
import { useAct, useBulk, useItems, useRestore, useSeenBelow, useSources, useTaxonomy } from "../hooks";
import { useShortcuts } from "../shortcuts";
import { FilterBar } from "./FilterBar";
import { ItemDetail } from "./ItemDetail";
import { ItemList } from "./ItemList";
import { HelpDialog, SnoozeMenu, Toast } from "./Overlays";
import { StateView } from "./StateView";

const DONE_TEXT: Record<Action, string> = {
  open: "Opened",
  done: "Marked done",
  dismiss: "Dismissed",
  snooze: "Snoozed",
  reopen: "Reopened",
  star: "Starred",
  unstar: "Unstarred",
};

const errorText = (error: unknown): string => (error as Error).message;

interface Props {
  filters: Filters;
  openId: string | null;
  onFilters: (filters: Filters) => void;
  onOpen: (id: string | null) => void;
}

interface Message {
  text: string;
  undo?: () => void;
}

export function Inbox({ filters, openId, onFilters, onOpen }: Props) {
  const items = useItems(filters);
  const sources = useSources();
  const taxonomy = useTaxonomy();
  const act = useAct();
  const bulk = useBulk();
  const restore = useRestore();
  const seenBelow = useSeenBelow();
  const [focusedId, setFocusedId] = useState<string | null>(null);
  const [picked, setSelected] = useState<ReadonlySet<string>>(new Set());
  const [snoozing, setSnoozing] = useState<string[] | null>(null);
  const [help, setHelp] = useState(false);
  const [message, setMessage] = useState<Message | null>(null);

  const list = useMemo(() => items.data?.items ?? [], [items.data]);
  const sourceNames = useMemo(
    () =>
      [...new Set([...(sources.data ?? []).map((s) => s.name), ...(filters.source ? [filters.source] : [])])].sort(),
    [sources.data, filters.source],
  );
  const focused = list.find((i) => i.id === focusedId) ?? list[0];

  // Items that left the list (done, filtered out) are no longer selected.
  const selected = useMemo(() => new Set([...picked].filter((id) => list.some((i) => i.id === id))), [picked, list]);

  const targets = useCallback((): string[] => {
    if (selected.size > 0) return [...selected];
    return focused ? [focused.id] : [];
  }, [selected, focused]);

  const perform = useCallback(
    async (action: Action, ids: string[], hours?: number) => {
      try {
        if (ids.length === 1) {
          const id = ids[0] as string;
          const result = await act.mutateAsync({ id, action, hours });
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
          setSelected(new Set());
          setMessage({ text: `${DONE_TEXT[action]}: ${result.changed} items` });
        }
      } catch (error) {
        setMessage({ text: errorText(error) });
      }
    },
    [act, bulk, restore],
  );

  const move = useCallback(
    (step: number) => {
      if (list.length === 0) return;
      const index = Math.max(
        0,
        list.findIndex((i) => i.id === focused?.id),
      );
      setFocusedId((list[Math.min(list.length - 1, Math.max(0, index + step))] as Item).id);
    },
    [list, focused],
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
      d: () => {
        void perform("dismiss", targets());
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
    [move, open, perform, targets, toggle, focused, message],
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
        onFocus={setFocusedId}
        onOpen={open}
        onToggle={toggle}
      />
    );
  }

  return (
    <div className="inbox">
      <FilterBar
        filters={filters}
        channels={(taxonomy.data?.channels ?? []).map((c) => c.name)}
        kinds={taxonomy.data?.kinds ?? []}
        sources={sourceNames}
        onChange={onFilters}
      />
      <div className="toolbar">
        <span>{items.data ? `${list.length} of ${items.data.total}` : ""}</span>
        <button
          type="button"
          onClick={() => {
            seenBelow.mutate("P1");
          }}
        >
          Mark P2 and P3 as seen
        </button>
        <button
          type="button"
          onClick={() => {
            setHelp(true);
          }}
        >
          Shortcuts
        </button>
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
              void perform("dismiss", [...selected]);
            }}
          >
            Dismiss
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
              setSelected(new Set());
            }}
          >
            Clear
          </button>
        </div>
      )}
      <div className="columns">
        <div className="list">{content}</div>
        {openId && (
          <ItemDetail
            id={openId}
            onAction={(action) => {
              void perform(action, [openId]);
            }}
            onSnooze={() => {
              setSnoozing([openId]);
            }}
            onClose={() => {
              onOpen(null);
            }}
          />
        )}
      </div>
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
  );
}
