import { useEffect } from "react";
import type { Action, Filters, Sweep } from "../api/types";
import { useSweep } from "../hooks";

const CHOICES: { action: Action; label: string }[] = [
  { action: "done", label: "done" },
  { action: "open", label: "seen" },
];

interface Props {
  filters: Filters;
  onClose: () => void;
  onDone: (result: Sweep, action: Action) => void;
}

/** Act on everything the current selection matches: says how many first, shows some, and asks. */
export function SweepDialog({ filters, onClose, onDone }: Props) {
  const count = useSweep();
  const apply = useSweep();
  const { mutate } = count;
  useEffect(() => {
    mutate({ filters, action: "done", dryRun: true });
  }, [mutate, filters]);

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
          <p className="hint">Nothing is deleted, and this teaches your profile nothing. You can undo it afterwards.</p>
          <div className="actions">
            {CHOICES.map((choice) => (
              <button
                key={choice.action}
                type="button"
                disabled={data.matched === 0}
                onClick={() => {
                  apply.mutate(
                    { filters, action: choice.action, dryRun: false },
                    {
                      onSuccess: (result) => {
                        onDone(result, choice.action);
                      },
                    },
                  );
                }}
              >
                Mark {data.matched} {choice.label}
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
