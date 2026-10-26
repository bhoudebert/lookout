import type { KeyboardEvent, MouseEvent } from "react";
import { clampWidth, DEFAULT_WIDTH, MAX_WIDTH, MIN_WIDTH } from "../listWidth";

const STEP = 24;

/** The bar between the list and the reader: drag it, or focus it and use the arrow keys. */
export function ColumnResizer({ width, onChange }: { width: number; onChange: (width: number) => void }) {
  const drag = (down: MouseEvent) => {
    down.preventDefault();
    const from = down.clientX;
    const move = (e: globalThis.MouseEvent) => {
      onChange(clampWidth(width + e.clientX - from));
    };
    const stop = () => {
      window.removeEventListener("mousemove", move);
      window.removeEventListener("mouseup", stop);
    };
    window.addEventListener("mousemove", move);
    window.addEventListener("mouseup", stop);
  };
  const press = (e: KeyboardEvent) => {
    const next: Record<string, number> = {
      ArrowLeft: width - (e.shiftKey ? STEP * 4 : STEP),
      ArrowRight: width + (e.shiftKey ? STEP * 4 : STEP),
      Home: MIN_WIDTH,
      End: MAX_WIDTH,
      Enter: DEFAULT_WIDTH,
    };
    const target = next[e.key];
    if (target === undefined) return;
    e.preventDefault();
    onChange(clampWidth(target));
  };
  return (
    // A splitter is an interactive widget (WAI-ARIA window splitter): focusable, with keys and a drag.
    /* eslint-disable jsx-a11y/no-noninteractive-element-interactions, jsx-a11y/no-noninteractive-tabindex */
    <div
      className="resizer"
      role="separator"
      aria-orientation="vertical"
      aria-label="List width"
      aria-valuenow={width}
      aria-valuemin={MIN_WIDTH}
      aria-valuemax={MAX_WIDTH}
      tabIndex={0}
      onMouseDown={drag}
      onKeyDown={press}
      onDoubleClick={() => {
        onChange(DEFAULT_WIDTH);
      }}
    />
    /* eslint-enable jsx-a11y/no-noninteractive-element-interactions, jsx-a11y/no-noninteractive-tabindex */
  );
}
