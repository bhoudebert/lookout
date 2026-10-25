import type { Channel } from "../api/types";
import { categoryRows } from "../categories";
import { CategoryIcon } from "./CategoryIcon";

interface Props {
  channels: Channel[];
  /** The category the inbox is filtered on, or an empty string for all. */
  selected: string;
  onSelect: (path: string) => void;
}

/** The categories beside the inbox: one click filters on a category and everything under it. */
export function CategoryTree({ channels, selected, onSelect }: Props) {
  const rows = categoryRows(channels);
  const everything = rows.filter((r) => r.depth === 0).reduce((sum, r) => sum + r.total, 0);
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
            <span className="count">{everything}</span>
          </button>
        </li>
        {rows.map((row) => (
          <li key={row.path}>
            <button
              type="button"
              style={{ paddingLeft: `${0.6 + row.depth * 1.1}rem` }}
              data-depth={row.depth}
              title={row.description || row.path}
              aria-current={selected === row.path ? "true" : undefined}
              onClick={() => {
                onSelect(row.path);
              }}
            >
              <span>
                <CategoryIcon icon={row.icon} />
                {row.name}
              </span>
              <span className="count">{row.total}</span>
            </button>
          </li>
        ))}
      </ul>
    </nav>
  );
}
