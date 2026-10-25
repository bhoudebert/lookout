import { useRunStatus } from "../hooks";

const clock = (iso: string): string =>
  new Date(iso).toLocaleTimeString(undefined, { hour: "2-digit", minute: "2-digit" });

/** The foot of the sidebar: whether the watch is running, and when it last finished. */
export function SideFoot() {
  const { data: run } = useRunStatus();
  if (!run) return null;
  let text = "No run yet";
  if (run.running) text = "Running now";
  else if (run.error) text = "The last run failed";
  else if (run.finished_at) text = `Last run ${clock(run.finished_at)}`;
  return (
    <p className="side-foot">
      <span className={`live${run.error ? " failed" : ""}`} aria-hidden="true" />
      {text}
    </p>
  );
}
