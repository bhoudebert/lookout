import type { components } from "./schema";

type Schemas = components["schemas"];

export type Item = Schemas["ItemOut"];
export type ItemDetail = Schemas["ItemDetail"];
export type ItemPage = Schemas["ItemPage"];
export type ActionResult = Schemas["ActionOut"];
export type Undo = Schemas["UndoOut"];
export type Source = Schemas["SourceOut"];
export type RunStatus = Schemas["RunOut"];
export type Action = Schemas["ActionIn"]["action"];
export type Taxonomy = Schemas["TaxonomyOut"];
export type SourceType = Schemas["SourceTypeOut"];
export type SourceField = Schemas["FieldOut"];
export type SourceBody = Schemas["SourceBody"];
export type SourceCreate = Schemas["SourceCreate"];
export type Channel = Schemas["ChannelOut"];
export type Sweep = Schemas["SweepOut"];
export type UndoEntry = Schemas["UndoEntry"];
export type RefileResult = Schemas["RefileOut"];
export type Priority = "P0" | "P1" | "P2" | "P3";
export const PRIORITIES: readonly Priority[] = ["P0", "P1", "P2", "P3"];

/** The views of the inbox the state selector offers. */
export type View = "inbox" | "snoozed" | "done" | "dismissed" | "expired" | "all";

/** Triage orders by priority; Latest is strictly newest first (ADR 0016). */
export type Order = "priority" | "date";

/** How old the items shown may be: everything, or older or newer than some days. */
export type Age = "" | "older7" | "older14" | "older30" | "newer7";
export const AGES: { value: Age; label: string }[] = [
  { value: "", label: "Any age" },
  { value: "newer7", label: "Newer than a week" },
  { value: "older7", label: "Older than a week" },
  { value: "older14", label: "Older than 2 weeks" },
  { value: "older30", label: "Older than a month" },
];

export interface Filters {
  priorities: Priority[];
  channel: string;
  source: string;
  view: View;
  starred: boolean;
  text: string;
  order: Order;
  age: Age;
}

export const NO_FILTERS: Filters = {
  priorities: [],
  channel: "",
  source: "",
  view: "inbox",
  starred: false,
  text: "",
  order: "priority",
  age: "",
};
