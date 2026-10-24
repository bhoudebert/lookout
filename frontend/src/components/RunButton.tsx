import { useEffect, useRef } from "react";
import { useRefresh, useRunStatus, useStartRun } from "../hooks";

export function RunButton() {
  const status = useRunStatus();
  const start = useStartRun();
  const refresh = useRefresh();
  const running = status.data?.running ?? false;
  const wasRunning = useRef(false);

  useEffect(() => {
    if (wasRunning.current && !running) void refresh();
    wasRunning.current = running;
  }, [running, refresh]);

  const last = status.data;
  let summary = "";
  if (running) summary = "Running…";
  else if (last?.error) summary = `Last run failed: ${last.error}`;
  else if (last?.finished_at) {
    const fresh = last.sources.reduce((sum, s) => sum + s.new, 0);
    summary = `Last run: ${fresh} new, ${last.enriched} read`;
    if (last.waiting > 0) summary += `, ${last.waiting} waiting for the model`;
  }
  return (
    <div className="run">
      <button
        type="button"
        disabled={running || start.isPending}
        onClick={() => {
          start.mutate();
        }}
      >
        Run now
      </button>
      <span
        role="status"
        title={
          last && last.waiting > 0 && !running
            ? "The daily model limit was reached. The rest are read tomorrow, in order of urgency, or raise llm.daily_limit."
            : undefined
        }
      >
        {summary}
      </span>
    </div>
  );
}
