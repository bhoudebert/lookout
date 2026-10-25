import type { Action, Rating } from "../api/types";
import { useItem } from "../hooks";
import { until, webUrl } from "../format";
import { PriorityBadge } from "./PriorityBadge";
import { DoneButton, RatingButtons } from "./RatingButtons";

interface Props {
  id: string;
  onAction: (action: Action) => void;
  onRate: (rating: Exclude<Rating, 0>) => void;
  onSnooze: () => void;
  onClose: () => void;
}

export function ItemDetail({ id, onAction, onRate, onSnooze, onClose }: Props) {
  const query = useItem(id);
  if (query.isPending)
    return (
      <aside className="detail" aria-busy="true">
        Loading…
      </aside>
    );
  if (query.isError) {
    return (
      <aside className="detail" role="alert">
        {query.error.message}
        <button type="button" onClick={onClose}>
          Close
        </button>
      </aside>
    );
  }
  const { item, body, explanation } = query.data;
  const tags = [...new Set([...item.feed_tags, ...item.tags])];
  const closed = item.state === "done" || item.state === "snoozed";
  return (
    <aside className="detail" aria-label="Item detail">
      <button type="button" className="close" onClick={onClose}>
        Close
      </button>
      <h2>{item.title}</h2>
      <p>
        <PriorityBadge item={item} />
      </p>
      {item.action_needed && <p className="action-needed">Action needed</p>}
      {item.summary && <p className="summary">{item.summary}</p>}
      <p className="facets">
        <span className="channel">{item.channel}</span>
        {item.unread && <> · not read yet</>}
        {item.author && <> · by {item.author}</>}
      </p>
      {tags.length > 0 && (
        <ul className="tags" aria-label="Tags">
          {tags.map((tag) => (
            <li key={tag}>{tag}</li>
          ))}
        </ul>
      )}
      <p className="excerpt">{body}</p>
      <p>
        {webUrl(item.url) ? (
          <a href={webUrl(item.url)} target="_blank" rel="noreferrer noopener">
            Open the original
          </a>
        ) : (
          <span>No web address to open</span>
        )}
      </p>
      {item.stack_matches.length > 0 && <p>Touches your stack: {item.stack_matches.join(", ")}</p>}
      {item.snoozed_until && <p>Snoozed until {until(item.snoozed_until)}</p>}
      <section aria-label="Why this rank">
        <h3>Why this rank</h3>
        <p>{explanation.priority_reason}</p>
        {explanation.model_score !== null && <p>Model score {explanation.model_score}</p>}
        <p>
          Your profile moves it {explanation.boost >= 0 ? "+" : ""}
          {explanation.boost} inside {explanation.priority}.
        </p>
        {explanation.contributions.length > 0 && (
          <ul>
            {explanation.contributions.map((c) => (
              <li key={c.feature}>
                {c.points >= 0 ? "+" : ""}
                {c.points} {c.feature}
              </li>
            ))}
          </ul>
        )}
      </section>
      <div className="actions" role="group" aria-label="Actions">
        {closed ? (
          <button
            type="button"
            onClick={() => {
              onAction("reopen");
            }}
          >
            Reopen
          </button>
        ) : (
          <>
            <DoneButton
              about={item.title}
              onDone={() => {
                onAction("done");
              }}
            />
            <button type="button" onClick={onSnooze}>
              Snooze…
            </button>
          </>
        )}
        <RatingButtons rating={item.rating} about={item.title} onRate={onRate} />
        <button
          type="button"
          aria-pressed={item.starred}
          onClick={() => {
            onAction(item.starred ? "unstar" : "star");
          }}
        >
          {item.starred ? "Unstar" : "Star"}
        </button>
      </div>
    </aside>
  );
}
