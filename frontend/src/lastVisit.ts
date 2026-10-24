const KEY = "lookout:last-visit";

/** When the inbox was last open, or null the first time; storage may be blocked, then there is no memory. */
export function readLastVisit(): Date | null {
  try {
    const stored = window.localStorage.getItem(KEY);
    return stored ? new Date(stored) : null;
  } catch {
    return null;
  }
}

export function rememberVisit(at: Date): void {
  try {
    window.localStorage.setItem(KEY, at.toISOString());
  } catch {
    // Without storage the divider simply never shows.
  }
}
