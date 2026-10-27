const KEY = "lookout:list-width";

export const MIN_WIDTH = 300;
export const MAX_WIDTH = 900;
export const DEFAULT_WIDTH = 480;

export function clampWidth(width: number): number {
  return Math.min(MAX_WIDTH, Math.max(MIN_WIDTH, Math.round(width)));
}

/** How wide the list was left, or the default; storage may be blocked, then it is never remembered. */
export function readListWidth(): number {
  try {
    const stored = Number(window.localStorage.getItem(KEY));
    return stored > 0 ? clampWidth(stored) : DEFAULT_WIDTH;
  } catch {
    return DEFAULT_WIDTH;
  }
}

export function rememberListWidth(width: number): void {
  try {
    window.localStorage.setItem(KEY, String(width));
  } catch {
    // Without storage the list is back to its default width at the next visit.
  }
}
