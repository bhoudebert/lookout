import type { Channel } from "../api/types";
import { categoryRows, inboxTotal } from "../categories";

interface Props {
  channels: Channel[];
  /** The category the inbox is filtered on, or an empty string for all. */
  selected: string;
  onSelect: (path: string) => void;
}

/** The categories beside the inbox: one click filters on a category and everything under it. */
export function CategoryTree({ channels, selected, onSelect }: Props) {
  const rows = categoryRows(channels);
  return (
    <nav className="tree" aria-label="Categories">
      <p className="tree-title" aria-hidden="true">
        Categories
      </p>
      <ul>
        <li>
          <button
            type="button"
            aria-current={selected === "" ? "true" : undefined}
            onClick={() => {
              onSelect("");
            }}
          >
            <span>All</span>
            <span className="count">{inboxTotal(channels)}</span>
          </button>
        </li>
        {rows.map((row) => (
          <li key={row.path}>
            <button
              type="button"

              data-depth={row.depth}
              title={row.description || row.path}
              aria-current={selected === row.path ? "true" : undefined}
              onClick={() => {
                onSelect(row.path);
              }}
            >
              <span>{row.name}</span>
              <span className="count">{row.total}</span>
            </button>
          </li>
        ))}
      </ul>
    </nav>
  );
}
