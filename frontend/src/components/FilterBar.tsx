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
    <>
      <div className="tabs" role="tablist" aria-label="View">
        {VIEWS.map((v) => (
          <button
            key={v.value}
            type="button"
            role="tab"
            aria-selected={filters.view === v.value}
            onClick={() => {
              onChange({ ...filters, view: v.value });
            }}
          >
            {v.label}
          </button>
        ))}
      </div>
      <form
        className="filters"
        role="search"
        aria-label="Filter the inbox"
        onSubmit={(e) => {
          e.preventDefault();
        }}
      >
        <label className="search">
          <span className="caption">Search</span>
          <input
            type="search"
            value={filters.text}
            placeholder="Title, summary, tag"
            onChange={(e) => {
              onChange({ ...filters, text: e.target.value });
            }}
          />
        </label>
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
        <label>
          <span className="caption">Source</span>
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
          <span className="caption">Age</span>
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
      </form>
    </>
  );
}
