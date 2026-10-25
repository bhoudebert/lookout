import type { Channel } from "./api/types";

export const SEP = " > ";

export interface CategoryRow {
  path: string;
  /** The last name of the path. */
  name: string;
  depth: number;
  description: string;
  /** One emoji, or an empty string. */
  icon: string;
  /** Items filed exactly here. */
  items: number;
  /** Items filed here or anywhere under it. */
  total: number;
  sources: string[];
}

const within = (path: string, ancestor: string) => path === ancestor || path.startsWith(ancestor + SEP);

/** The categories as the rows of a tree, parents before their children, Other last, with totals that include children. */
export function categoryRows(channels: Channel[]): CategoryRow[] {
  const byPath = (a: Channel, b: Channel) => Number(a.name > b.name) - Number(a.name < b.name);
  const ordered = [...channels].sort(byPath).sort((a, b) => Number(a.name === "Other") - Number(b.name === "Other"));
  return ordered.map((channel) => {
    const parts = channel.name.split(SEP);
    return {
      path: channel.name,
      name: parts[parts.length - 1] as string,
      depth: parts.length - 1,
      description: channel.description,
      icon: channel.icon,
      items: channel.items,
      total: channels.filter((c) => within(c.name, channel.name)).reduce((sum, c) => sum + c.items, 0),
      sources: channel.sources ?? [],
    };
  });
}

/** What the inbox holds: the items of the top-level categories, each counted with everything under it. */
export const inboxTotal = (channels: Channel[]): number =>
  categoryRows(channels)
    .filter((r) => r.depth === 0)
    .reduce((sum, r) => sum + r.total, 0);
