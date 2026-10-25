import { useRunStatus } from "../hooks";

/** The last run at a glance: what it fetched, how much of that was new, and what waits for the model. */
export function RunStrip() {
  const { data: run } = useRunStatus();
  if (!run) return null;
  if (run.running) return <p className="strip">A run is going…</p>;
  if (run.error) return <p className="strip failed">The last run failed: {run.error}</p>;
  if (!run.finished_at) return null;
  const at = new Date(run.finished_at).toLocaleTimeString(undefined, { hour: "2-digit", minute: "2-digit" });
  const fetched = run.sources.reduce((sum, s) => sum + s.fetched, 0);
  const fresh = run.sources.reduce((sum, s) => sum + s.new, 0);
  const known = fetched - fresh;
  return (
    <div className="strip" role="group" aria-label="The last run">
      <p className="strip-cap">
        <span>Last run, {at}</span>
        <span>
          <strong>{fetched}</strong> fetched · <strong>{fresh}</strong> new
          {run.waiting > 0 && <> · {run.waiting} waiting for the model</>}
        </span>
      </p>
      {fetched > 0 && (
        <div className="strip-bar" aria-hidden="true">
          <i className="new" style={{ flexGrow: fresh }} />
          <i className="known" style={{ flexGrow: known }} />
        </div>
      )}
      <p className="strip-legend">
        <span className="dot new" /> {fresh} new <span className="dot known" /> {known} already known
      </p>
    </div>
  );
}
