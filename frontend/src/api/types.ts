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
export type Priority = "P0" | "P1" | "P2" | "P3";
export const PRIORITIES: readonly Priority[] = ["P0", "P1", "P2", "P3"];

/** The views of the inbox the state selector offers. */
export type View = "inbox" | "snoozed" | "done" | "dismissed" | "all";

export interface Filters {
  priorities: Priority[];
  category: string;
  source: string;
  view: View;
  starred: boolean;
  text: string;
}

export const NO_FILTERS: Filters = {
  priorities: [],
  category: "",
  source: "",
  view: "inbox",
  starred: false,
  text: "",
};
