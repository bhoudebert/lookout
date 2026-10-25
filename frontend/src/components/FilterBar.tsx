import { AGES, PRIORITIES } from "../api/types";
import type { Age, Filters, Order, Priority, View } from "../api/types";

export const VIEWS: { value: View; label: string }[] = [
  { value: "inbox", label: "Inbox" },
  { value: "snoozed", label: "Snoozed" },
  { value: "done", label: "Done" },
  { value: "expired", label: "Expired" },
  { value: "all", label: "Everything" },
];

const ORDERS: { value: Order; label: string; hint: string }[] = [
  { value: "priority", label: "Triage", hint: "Most urgent first" },
  { value: "date", label: "Latest", hint: "Newest first" },
];

interface Props {
  filters: Filters;
  sources: string[];
  onChange: (filters: Filters) => void;
}

export function FilterBar({ filters, sources, onChange }: Props) {
  const togglePriority = (priority: Priority) => {
    const next = filters.priorities.includes(priority)
      ? filters.priorities.filter((p) => p !== priority)
      : [...filters.priorities, priority];
    onChange({ ...filters, priorities: next });
  };
  return (
    <form
      className="filters"
      role="search"
      aria-label="Filter the inbox"
      onSubmit={(e) => {
        e.preventDefault();
      }}
    >
      <div className="field">
        <span className="caption" aria-hidden="true">
          Priority
        </span>
        <div className="chips" role="group" aria-label="Priority">
          {PRIORITIES.map((priority) => (
            <button
              key={priority}
              type="button"
              className={`chip ${priority.toLowerCase()}`}
              aria-pressed={filters.priorities.includes(priority)}
              onClick={() => {
                togglePriority(priority);
              }}
            >
              {priority}
            </button>
          ))}
        </div>
      </div>
      <div className="field">
        <span className="caption" aria-hidden="true">
          Order
        </span>
        <div className="chips" role="group" aria-label="Order">
          {ORDERS.map((order) => (
            <button
              key={order.value}
              type="button"
              className="chip wide"
              title={order.hint}
              aria-pressed={filters.order === order.value}
              onClick={() => {
                onChange({ ...filters, order: order.value });
              }}
            >
              {order.label}
            </button>
          ))}
        </div>
      </div>
      <label>
        View
        <select
          value={filters.view}
          onChange={(e) => {
            onChange({ ...filters, view: e.target.value as View });
          }}
        >
          {VIEWS.map((v) => (
            <option key={v.value} value={v.value}>
              {v.label}
            </option>
          ))}
        </select>
      </label>
      <label>
        Source
        <select
          value={filters.source}
          onChange={(e) => {
            onChange({ ...filters, source: e.target.value });
          }}
        >
          <option value="">All</option>
          {sources.map((s) => (
            <option key={s} value={s}>
              {s}
            </option>
          ))}
        </select>
      </label>
      <label>
        Age
        <select
          value={filters.age}
          onChange={(e) => {
            onChange({ ...filters, age: e.target.value as Age });
          }}
        >
          {AGES.map((a) => (
            <option key={a.value} value={a.value}>
              {a.label}
            </option>
          ))}
        </select>
      </label>
      <label className="check">
        <input
          type="checkbox"
          checked={filters.starred}
          onChange={(e) => {
            onChange({ ...filters, starred: e.target.checked });
          }}
        />
        Starred
      </label>
      <label>
        Search
        <input
          type="search"
          value={filters.text}
          placeholder="title, summary, tag"
          onChange={(e) => {
            onChange({ ...filters, text: e.target.value });
          }}
        />
      </label>
    </form>
  );
}
