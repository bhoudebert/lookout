import type { Item } from "../api/types";
import { timeAgo } from "../format";
import { PriorityBadge } from "./PriorityBadge";

interface Props {
  items: Item[];
  focusedId: string | null;
  selected: ReadonlySet<string>;
  now: Date;
  onFocus: (id: string) => void;
  onOpen: (id: string) => void;
  onToggle: (id: string) => void;
}

export function ItemList({ items, focusedId, selected, now, onFocus, onOpen, onToggle }: Props) {
  return (
    <ul className="items" aria-label="Items">
      {items.map((item) => (
        <li
          key={item.id}
          className={`item ${item.state}${item.id === focusedId ? " focused" : ""}`}
          aria-current={item.id === focusedId ? "true" : undefined}
        >
          <input
            type="checkbox"
            aria-label={`Select ${item.title}`}
            checked={selected.has(item.id)}
            onChange={() => {
              onToggle(item.id);
            }}
          />
          <div className="item-body">
            <div className="item-head">
              <PriorityBadge item={item} />
              {item.starred && (
                <span className="star" role="img" aria-label="Starred">
                  ★
                </span>
              )}
              <button
                type="button"
                className="title"
                onFocus={() => {
                  onFocus(item.id);
                }}
                onClick={() => {
                  onOpen(item.id);
                }}
              >
                {item.title}
              </button>
            </div>
            <p className="meta">
              <span className="channel">{item.channel}</span> · {item.sources.join(", ")}
              {item.author && <> · by {item.author}</>} · {timeAgo(item.published_at, now)}
              {item.state !== "new" && item.state !== "seen" && <> · {item.state}</>}
              {item.unread && <> · waiting for the model</>}
              {item.enrichment_failed && <> · the model could not read it</>}
            </p>
            {item.tags.length > 0 && (
              <p className="tags" aria-label="Tags">
                {item.tags.slice(0, 4).map((tag) => (
                  <span key={tag}>#{tag}</span>
                ))}
              </p>
            )}
            {item.summary && <p className="summary">{item.summary}</p>}
          </div>
        </li>
      ))}
    </ul>
  );
}
