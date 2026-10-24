import { PRIORITIES } from "../api/types";
import type { Filters, Priority, View } from "../api/types";

const VIEWS: { value: View; label: string }[] = [
  { value: "inbox", label: "Inbox" },
  { value: "snoozed", label: "Snoozed" },
  { value: "done", label: "Done" },
  { value: "dismissed", label: "Dismissed" },
  { value: "all", label: "Everything" },
];

interface Props {
  filters: Filters;
  channels: string[];
  kinds: string[];
  sources: string[];
  onChange: (filters: Filters) => void;
}

export function FilterBar({ filters, channels, kinds, sources, onChange }: Props) {
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
        Category
        <select
          value={filters.channel}
          onChange={(e) => {
            onChange({ ...filters, channel: e.target.value });
          }}
        >
          <option value="">All</option>
          {channels.map((c) => (
            <option key={c} value={c}>
              {c}
            </option>
          ))}
        </select>
      </label>
      <label>
        Kind
        <select
          value={filters.kind}
          onChange={(e) => {
            onChange({ ...filters, kind: e.target.value });
          }}
        >
          <option value="">All</option>
          {kinds.map((k) => (
            <option key={k} value={k}>
              {k}
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
