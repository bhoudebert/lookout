import { useEffect } from "react";

export type ShortcutHandlers = Partial<Record<string, () => void>>;

const BUTTON_LIKE = new Set(["checkbox", "radio", "button"]);

/** Fields where keys mean text; a checkbox keeps the shortcuts alive after it is clicked. */
function isTyping(target: HTMLElement): boolean {
  if (target.tagName === "INPUT") return !BUTTON_LIKE.has((target as HTMLInputElement).type);
  return target.tagName === "TEXTAREA" || target.tagName === "SELECT";
}

/** Single-key shortcuts, ignored while the user types in a field or holds a modifier. */
export function useShortcuts(handlers: ShortcutHandlers, enabled = true): void {
  useEffect(() => {
    if (!enabled) return;
    const onKey = (event: KeyboardEvent) => {
      const target = event.target as HTMLElement;
      if (isTyping(target) || event.ctrlKey || event.metaKey || event.altKey) return;
      const handler = handlers[event.key];
      if (handler) {
        event.preventDefault();
        handler();
      }
    };
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("keydown", onKey);
    };
  }, [handlers, enabled]);
}
