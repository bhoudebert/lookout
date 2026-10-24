import { useState } from "react";
import type { Source, SourceType } from "../api/types";
import { useManage, useSetSource, useSourceTypes, useSources, useTaxonomy } from "../hooks";
import { until } from "../format";
import { ChannelsPanel } from "./ChannelsPanel";
import { SourceForm } from "./SourceForm";
import { StateView } from "./StateView";

const message = (error: unknown): string => (error as Error).message;

const hasType = (types: SourceType[]): types is [SourceType, ...SourceType[]] => types.length > 0;

/** Rivers and the channels they flow to: everything is managed here (ADR 0013). */
export function SourcesView() {
  const sources = useSources();
  const types = useSourceTypes();
  const taxonomy = useTaxonomy();
  const setSource = useSetSource();
  const { addSource, updateSource, deleteSource } = useManage();
  const [form, setForm] = useState<"none" | "add" | Source>("none");

  if (sources.isPending || types.isPending || taxonomy.isPending) return <StateView kind="loading" />;
  if (sources.isError || types.isError || taxonomy.isError) {
    const error = sources.error ?? types.error ?? taxonomy.error;
    return (
      <StateView
        kind="error"
        message={message(error)}
        onRetry={() => {
          void sources.refetch();
          void types.refetch();
          void taxonomy.refetch();
        }}
      />
    );
  }
  if (!hasType(types.data)) {
    return <StateView kind="error" message="This Lookout knows no type of source." />;
  }
  const channelNames = taxonomy.data.channels.map((c) => c.name);
  const saving = addSource.isPending || updateSource.isPending;
  const failure = form === "add" ? addSource.error : updateSource.error;
  const close = () => {
    setForm("none");
    addSource.reset();
    updateSource.reset();
  };

  return (
    <>
      <section aria-label="Sources">
        <h2>Sources</h2>
        <p className="hint">The rivers that flow into your inbox.</p>
        {(setSource.isError || deleteSource.isError) && (
          <p role="alert" className="form-error">
            {message(setSource.error ?? deleteSource.error)}
          </p>
        )}
        {sources.data.length === 0 ? (
          <StateView kind="empty" message="No source yet. Add one to start filling the inbox." />
        ) : (
          <table>
            <thead>
              <tr>
                <th>Name</th>
                <th>Type</th>
                <th>Channels</th>
                <th>Last run</th>
                <th>Items</th>
                <th>Last error</th>
                <th>Enabled</th>
                <th>Manage</th>
              </tr>
            </thead>
            <tbody>
              {sources.data.map((s) => (
                <tr key={s.name}>
                  <th scope="row">{s.name}</th>
                  <td>{s.type}</td>
                  <td>{s.channels.length > 0 ? s.channels.join(", ") : "any"}</td>
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
                  <td>
                    <button
                      type="button"
                      aria-label={`Edit ${s.name}`}
                      onClick={() => {
                        setForm(s);
                      }}
                    >
                      Edit
                    </button>
                    <button
                      type="button"
                      aria-label={`Delete ${s.name}`}
                      onClick={() => {
                        deleteSource.mutate(s.name);
                      }}
                    >
                      Delete
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
        {form === "none" ? (
          <p>
            <button
              type="button"
              onClick={() => {
                setForm("add");
              }}
            >
              Add a source
            </button>
          </p>
        ) : (
          <SourceForm
            key={form === "add" ? "add" : form.name}
            types={types.data}
            channels={channelNames}
            source={form === "add" ? undefined : form}
            error={failure ? message(failure) : undefined}
            busy={saving}
            onCancel={close}
            onSave={(name, body) => {
              if (form === "add") addSource.mutate({ name, ...body }, { onSuccess: close });
              else updateSource.mutate({ name: form.name, body }, { onSuccess: close });
            }}
          />
        )}
      </section>
      <ChannelsPanel channels={taxonomy.data.channels} />
    </>
  );
}
