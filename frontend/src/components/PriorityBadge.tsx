import type { Item } from "../api/types";

/** Priority is always written out: colour alone would not reach everyone. */
export function PriorityBadge({ item }: { item: Pick<Item, "priority" | "priority_label"> }) {
  return (
    <span className={`badge ${item.priority.toLowerCase()}`}>
      <strong>{item.priority}</strong> <span className="badge-label">{item.priority_label}</span>
    </span>
  );
}
