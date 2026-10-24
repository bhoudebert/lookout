import { useEffect } from "react";

export const SNOOZES: { label: string; hours: number }[] = [
  { label: "1 hour", hours: 1 },
  { label: "4 hours", hours: 4 },
  { label: "Tomorrow", hours: 24 },
  { label: "Next week", hours: 168 },
];

export function SnoozeMenu({ onPick, onClose }: { onPick: (hours: number) => void; onClose: () => void }) {
  return (
    <div className="modal" role="dialog" aria-modal="true" aria-label="Snooze until">
      <h2>Snooze for</h2>
      <div className="actions">
        {SNOOZES.map((s) => (
          <button
            key={s.hours}
            type="button"
            onClick={() => {
              onPick(s.hours);
            }}
          >
            {s.label}
          </button>
        ))}
      </div>
      <button type="button" onClick={onClose}>
        Cancel
      </button>
    </div>
  );
}

const KEYS: [string, string][] = [
  ["j / k", "next / previous item"],
  ["o or Enter", "open the item"],
  ["e", "mark done"],
  ["d", "dismiss"],
  ["s", "snooze"],
  ["*", "star or unstar"],
  ["x", "select for a bulk action"],
  ["u", "undo the last action"],
  ["?", "show this help"],
];

export function HelpDialog({ onClose }: { onClose: () => void }) {
  return (
    <div className="modal" role="dialog" aria-modal="true" aria-label="Keyboard shortcuts">
      <h2>Keyboard shortcuts</h2>
      <dl>
        {KEYS.map(([key, what]) => (
          <div key={key}>
            <dt>
              <kbd>{key}</kbd>
            </dt>
            <dd>{what}</dd>
          </div>
        ))}
      </dl>
      <button type="button" onClick={onClose}>
        Close
      </button>
    </div>
  );
}

const TOAST_MS = 8000;

export function Toast({ message, onUndo, onDismiss }: { message: string; onUndo?: () => void; onDismiss: () => void }) {
  useEffect(() => {
    const timer = setTimeout(onDismiss, TOAST_MS);
    return () => {
      clearTimeout(timer);
    };
  }, [message, onDismiss]);
  return (
    <div className="toast" role="status">
      {message}
      {onUndo && (
        <button type="button" onClick={onUndo}>
          Undo
        </button>
      )}
    </div>
  );
}
