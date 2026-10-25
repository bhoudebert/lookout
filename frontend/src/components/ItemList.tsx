import { Fragment } from "react";
import type { Item, Rating } from "../api/types";
import { timeAgo } from "../format";
import { SourceMark } from "./SourceMark";
import { PriorityBadge } from "./PriorityBadge";
import { DoneButton, RatingButtons } from "./RatingButtons";

interface Props {
  items: Item[];
  focusedId: string | null;
  selected: ReadonlySet<string>;
  now: Date;
  /** The id of the first item seen on an earlier visit, to draw a line above it. */
  earlierFrom?: string | null;
  onFocus: (id: string) => void;
  onOpen: (id: string) => void;
  onToggle: (id: string) => void;
  onRate: (id: string, rating: Exclude<Rating, 0>) => void;
  onDone: (id: string) => void;
}

export function ItemList({
  items,
  focusedId,
  selected,
  now,
  earlierFrom,
  onFocus,
  onOpen,
  onToggle,
  onRate,
  onDone,
}: Props) {
  return (
    <ul className="items" aria-label="Items">
      {items.map((item, index) => (
        <Fragment key={item.id}>
          {item.id === earlierFrom && <li className="divider">{index} new since your last visit</li>}
          <li
            className={`item ${item.state}${item.id === focusedId ? " focused" : ""}`}
            aria-current={item.id === focusedId ? "true" : undefined}
          >
            <span className="lead">
              <SourceMark name={item.sources[0] ?? item.channel} />
              <input
                type="checkbox"
                aria-label={`Select ${item.title}`}
                checked={selected.has(item.id)}
                onChange={() => {
                  onToggle(item.id);
                }}
              />
            </span>
            <div className="item-body">
              <div className="item-head">
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
                {item.sources.join(", ")} · <span className="channel">{item.channel}</span>
                <span className="more-meta">
                  {item.author && <> · by {item.author}</>} · {timeAgo(item.published_at, now)}
                </span>
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
            <div className="item-side">
              <span className="age">{timeAgo(item.published_at, now).replace(" ago", "")}</span>
              <PriorityBadge item={item} />
            </div>
            <div className="item-actions">
              <RatingButtons
                rating={item.rating}
                about={item.title}
                onRate={(rating) => {
                  onRate(item.id, rating);
                }}
              />
              <DoneButton
                about={item.title}
                onDone={() => {
                  onDone(item.id);
                }}
              />
            </div>
          </li>
        </Fragment>
      ))}
    </ul>
  );
}
