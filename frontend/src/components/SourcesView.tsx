import { useSetSource, useSources } from "../hooks";
import { until } from "../format";
import { StateView } from "./StateView";

export function SourcesView() {
  const sources = useSources();
  const setSource = useSetSource();
  if (sources.isPending) return <StateView kind="loading" />;
  if (sources.isError)
    return <StateView kind="error" message={sources.error.message} onRetry={() => void sources.refetch()} />;
  if (sources.data.length === 0) {
    return <StateView kind="empty" message="No source is declared. Add some to lookout.yaml." />;
  }
  return (
    <section aria-label="Sources">
      <h2>Sources</h2>
      {setSource.isError && <p role="alert">{setSource.error.message}</p>}
      <table>
        <thead>
          <tr>
            <th>Name</th>
            <th>Kind</th>
            <th>Last run</th>
            <th>Items</th>
            <th>Last error</th>
            <th>Enabled</th>
          </tr>
        </thead>
        <tbody>
          {sources.data.map((s) => (
            <tr key={s.name}>
              <th scope="row">{s.name}</th>
              <td>{s.kind}</td>
              <td>{s.last_run ? until(s.last_run) : "never"}</td>
              <td>{s.items_seen}</td>
              <td>{s.last_error ?? "none"}</td>
              <td>
                <input
                  type="checkbox"
                  role="switch"
                  aria-label={`Enable ${s.name}`}
                  checked={s.enabled}
                  onChange={(e) => {
                    setSource.mutate({ name: s.name, enabled: e.target.checked });
                  }}
                />
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  );
}
