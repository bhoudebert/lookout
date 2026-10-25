import { useEffect } from "react";
import type { Filters, Sweep, SweepChoice } from "../api/types";
import { useSweep } from "../hooks";

interface Choice {
  choice: SweepChoice;
  /** On the button, after "Mark N" or by itself. */
  label: string;
  /** What the message says afterwards. */
  said: string;
}

const CLEARING: Choice[] = [
  { choice: { action: "done" }, label: "done", said: "Marked done" },
  { choice: { action: "open" }, label: "seen", said: "Opened" },
];
const RATING: Choice[] = [
  { choice: { rating: 1 }, label: "More like this", said: "More like this" },
  { choice: { rating: -1 }, label: "Less like this", said: "Less like this" },
  { choice: { rating: 0 }, label: "Clear the rating", said: "Rating cleared" },
];

interface Props {
  filters: Filters;
  onClose: () => void;
  /** Called with what was done and the words for the message. */
  onDone: (result: Sweep, said: string) => void;
}

/** Act on everything the current selection matches: says how many first, shows some, and asks. */
export function SweepDialog({ filters, onClose, onDone }: Props) {
  const count = useSweep();
  const apply = useSweep();
  const { mutate } = count;
  useEffect(() => {
    mutate({ filters, choice: { action: "done" }, dryRun: true });
  }, [mutate, filters]);

  const choose = (c: Choice) => {
    apply.mutate(
      { filters, choice: c.choice, dryRun: false },
      {
        onSuccess: (result) => {
          onDone(result, c.said);
        },
      },
    );
  };

  const data = count.data;
  const failure = count.error ?? apply.error;
  return (
    <div className="modal" role="dialog" aria-modal="true" aria-label="Act on everything shown">
      <h2>Act on everything this selection matches</h2>
      {failure && (
        <p role="alert" className="form-error">
          {failure.message}
        </p>
      )}
      {!data && !failure && <p className="hint">Counting…</p>}
      {data && (
        <>
          <p>
            <strong>{data.matched} items</strong> match, not only the ones loaded. For example:
          </p>
          <ul className="sample">
            {data.sample.map((item) => (
              <li key={item.id}>{item.title}</li>
            ))}
          </ul>
          <p className="hint">
            Nothing is deleted, and you can undo it afterwards. <strong>Done</strong> and <strong>seen</strong> teach
            your profile nothing. A <strong>thumb</strong> does, for every item at once, and leaves them in the inbox.
          </p>
          <div className="actions" role="group" aria-label="Clear">
            {CLEARING.map((c) => (
              <button
                key={c.label}
                type="button"
                disabled={data.matched === 0}
                onClick={() => {
                  choose(c);
                }}
              >
                Mark {data.matched} {c.label}
              </button>
            ))}
          </div>
          <div className="actions" role="group" aria-label="Rate">
            {RATING.map((c) => (
              <button
                key={c.label}
                type="button"
                disabled={data.matched === 0}
                onClick={() => {
                  choose(c);
                }}
              >
                {c.label} ({data.matched})
              </button>
            ))}
          </div>
        </>
      )}
      <button type="button" onClick={onClose}>
        Cancel
      </button>
    </div>
  );
}
