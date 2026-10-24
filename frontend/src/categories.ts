import type { Channel } from "./api/types";

export const SEP = " > ";

export interface CategoryRow {
  path: string;
  /** The last name of the path. */
  name: string;
  depth: number;
  description: string;
  /** Items filed exactly here. */
  items: number;
  /** Items filed here or anywhere under it. */
  total: number;
  sources: string[];
}

const within = (path: string, ancestor: string) => path === ancestor || path.startsWith(ancestor + SEP);

/** The categories as the rows of a tree, parents before their children, Other last, with totals that include children. */
export function categoryRows(declared: Channel[]): CategoryRow[] {
  // A path whose parent is missing (an older server stored it flat) still shows under its parent.
  const known = new Set(declared.map((c) => c.name));
  const implied: Channel[] = [];
  for (const channel of declared) {
    const parts = channel.name.split(SEP);
    for (let n = 1; n < parts.length; n++) {
      const path = parts.slice(0, n).join(SEP);
      if (!known.has(path)) {
        known.add(path);
        implied.push({ name: path, description: "", items: 0, sources: [] });
      }
    }
  }
  const channels = [...declared, ...implied].sort((a, b) => Number(a.name > b.name) - Number(a.name < b.name));
  const ordered = [...channels].sort((a, b) => Number(a.name === "Other") - Number(b.name === "Other"));
  return ordered.map((channel) => {
    const parts = channel.name.split(SEP);
    return {
      path: channel.name,
      name: parts[parts.length - 1] as string,
      depth: parts.length - 1,
      description: channel.description,
      items: channel.items,
      total: channels.filter((c) => within(c.name, channel.name)).reduce((sum, c) => sum + c.items, 0),
      sources: channel.sources ?? [],
    };
  });
}
