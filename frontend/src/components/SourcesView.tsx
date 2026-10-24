import { useState } from "react";
import type { Source, SourceType } from "../api/types";
import { useManage, useSetSource, useSourceTypes, useSources, useTaxonomy } from "../hooks";
import { until } from "../format";
import { GROUPS, PRESETS } from "../presets";
import type { Preset } from "../presets";
import { SourceForm } from "./SourceForm";
import { StateView } from "./StateView";

const message = (error: unknown): string => (error as Error).message;

const hasType = (types: SourceType[]): types is [SourceType, ...SourceType[]] => types.length > 0;

/** The rivers that flow into the inbox (ADR 0013). Categories are managed on their own page. */
export function SourcesView() {
  const sources = useSources();
  const types = useSourceTypes();
  const taxonomy = useTaxonomy();
  const setSource = useSetSource();
  const { addSource, updateSource, deleteSource, addChannel } = useManage();
  const [adding, setAdding] = useState<string | null>(null);
  const [problem, setProblem] = useState<string | null>(null);
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
  const urlOf = (settings: Record<string, unknown>) => settings.url;
  const missing = PRESETS.filter(
    (p) =>
      !sources.data.some(
        (s) => s.name === p.name || (urlOf(p.settings) !== undefined && urlOf(s.settings) === urlOf(p.settings)),
      ),
  );
  /** Add a suggested source, and the category it files in when that does not exist yet. */
  const addPreset = (preset: Preset) => {
    setProblem(null);
    setAdding(preset.name);
    const category = preset.category;
    const ready =
      category && !channelNames.includes(category.name)
        ? addChannel.mutateAsync({ name: category.name, description: category.description })
        : Promise.resolve();
    ready
      .then(() =>
        addSource.mutateAsync({
          name: preset.name,
          type: preset.type,
          settings: preset.settings,
          channels: category ? [category.name] : [],
          enabled: true,
        }),
      )
      .catch((error: unknown) => {
        setProblem(message(error));
      })
      .finally(() => {
        setAdding(null);
      });
  };
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
        <p className="hint">
          The rivers that flow into your inbox. Each says which <a href="/categories">categories</a> it may feed.
        </p>
        {(setSource.isError || deleteSource.isError) && (
          <p role="alert" className="form-error">
            {message(setSource.error ?? deleteSource.error)}
          </p>
        )}
        {problem && (
          <p role="alert" className="form-error">
            {problem}
          </p>
        )}
        {missing.length > 0 && (
          <div className="presets" role="group" aria-label="Suggested sources">
            <p className="hint">
              Start with a suggestion: each address was checked, and one click adds the source and the category it files
              in. Open a theme to see them.
            </p>
            {GROUPS.map((group) => {
              const inGroup = missing.filter((p) => p.group === group.id);
              if (inGroup.length === 0) return null;
              return (
                <details key={group.id}>
                  <summary>
                    {group.title} <span className="count">{inGroup.length}</span>
                  </summary>
                  <p className="hint">{group.about}</p>
                  <ul>
                    {inGroup.map((p) => (
                      <li key={p.name}>
                        <button
                          type="button"
                          disabled={adding !== null}
                          onClick={() => {
                            addPreset(p);
                          }}
                        >
                          + {p.name}
                        </button>
                        <span className="hint">{p.blurb}</span>
                      </li>
                    ))}
                  </ul>
                </details>
              );
            })}
          </div>
        )}
        {sources.data.length === 0 ? (
          <StateView kind="empty" message="No source yet. Add one to start filling the inbox." />
        ) : (
          <table>
            <thead>
              <tr>
                <th>Name</th>
                <th>Type</th>
                <th>Categories</th>
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
                  <td>{s.channels.length > 0 ? s.channels.join(", ") : "model decides"}</td>
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
    </>
  );
}
