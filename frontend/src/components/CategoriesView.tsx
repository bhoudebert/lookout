import { useState } from "react";
import type { RefileResult } from "../api/types";
import { categoryRows, SEP } from "../categories";
import type { CategoryRow } from "../categories";
import { useManage, useTaxonomy } from "../hooks";
import { StateView } from "./StateView";

const message = (error: unknown): string => (error as Error).message;

/** Starting points for someone whose only category is Other. One click adds one (with its parent). */
const SUGGESTIONS: { path: string; description: string }[] = [
  { path: "AI", description: "Models, agents and the tooling around them" },
  { path: "Dev > Rust", description: "The Rust language and its ecosystem" },
  { path: "Dev > Python", description: "Python and its ecosystem" },
  { path: "Dev > Web", description: "Browsers, frontend frameworks and the web platform" },
  { path: "Security", description: "Vulnerabilities, advisories and fixes in what I run" },
  { path: "Cloud", description: "Infrastructure, containers and hosting" },
  { path: "Data", description: "Databases, data engineering and analytics" },
];

function Category({
  row,
  onSave,
  onDelete,
}: {
  row: CategoryRow;
  onSave: (description: string) => void;
  onDelete: () => void;
}) {
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState(row.description);
  return (
    <li style={{ paddingLeft: `${row.depth * 1.5}rem` }}>
      <strong title={row.path}>{row.name}</strong>
      <span className="count">{row.total} items</span>
      {editing ? (
        <>
          <input
            aria-label={`Description of ${row.path}`}
            value={draft}
            onChange={(e) => {
              setDraft(e.target.value);
            }}
          />
          <button
            type="button"
            onClick={() => {
              onSave(draft);
              setEditing(false);
            }}
          >
            Save
          </button>
          <button
            type="button"
            onClick={() => {
              setEditing(false);
            }}
          >
            Cancel
          </button>
        </>
      ) : (
        <>
          <span className="hint">{row.description || "no description: it helps the model choose"}</span>
          <button
            type="button"
            aria-label={`Edit ${row.path}`}
            onClick={() => {
              setDraft(row.description);
              setEditing(true);
            }}
          >
            Edit
          </button>
          <button type="button" aria-label={`Delete ${row.path}`} onClick={onDelete}>
            Delete
          </button>
        </>
      )}
      <span className="hint feeders">
        {row.sources.length > 0 ? `fed by ${row.sources.join(", ")}` : "any source may file items here"}
      </span>
    </li>
  );
}

/** Categories, as one tree (ADR 0015): what you look at, from broad to specific. */
export function CategoriesView() {
  const taxonomy = useTaxonomy();
  const { addChannel, updateChannel, deleteChannel, refile, previewRefile } = useManage();
  const [name, setName] = useState("");
  const [parent, setParent] = useState("");
  const [description, setDescription] = useState("");
  const [problem, setProblem] = useState<string | null>(null);
  const [offer, setOffer] = useState<RefileResult | null>(null);

  if (taxonomy.isPending) return <StateView kind="loading" />;
  if (taxonomy.isError) {
    return (
      <StateView
        kind="error"
        message={message(taxonomy.error)}
        onRetry={() => {
          void taxonomy.refetch();
        }}
      />
    );
  }
  const channels = taxonomy.data.channels;
  const rows = categoryRows(channels);
  const missing = SUGGESTIONS.filter((s) => !channels.some((c) => c.name.toLowerCase() === s.path.toLowerCase()));

  /** Run one action; only the latest outcome is shown, so an old refusal never lingers. */
  const attempt = (action: Promise<unknown>, then?: () => void) => {
    setProblem(null);
    action.then(then, (error: unknown) => {
      setProblem(message(error));
    });
  };
  /** After a category appears, say how many items could move and let the user decide (ADR 0015). */
  const created = (add: Promise<unknown>, after?: () => void) => {
    attempt(
      add
        .then(() => previewRefile.mutateAsync())
        .then((preview) => {
          setOffer(preview.filed + preview.queued > 0 ? preview : null);
          after?.();
        }),
    );
  };

  return (
    <>
      <section aria-label="Categories">
        <h2>Categories</h2>
        <p className="hint">
          What you look at, from broad to specific: <em>Dev</em> contains <em>Dev &gt; Rust</em>. A source files its
          items in the categories you tick for it, or lets the model choose the most specific one that fits; the model
          uses Other only as a last resort.
        </p>
        {problem && (
          <p role="alert" className="form-error">
            {problem}
          </p>
        )}
        {offer && (
          <div className="nudge" role="note">
            <p>
              {offer.filed + offer.queued} items you already have could move: {offer.filed} by rule, {offer.queued} to
              be read again by the model at the next run.
            </p>
            <button
              type="button"
              onClick={() => {
                attempt(refile.mutateAsync(), () => {
                  setOffer(null);
                });
              }}
            >
              File them now
            </button>
            <button
              type="button"
              onClick={() => {
                setOffer(null);
              }}
            >
              Not now
            </button>
          </div>
        )}
        {missing.length > 0 && (
          <div className="suggestions" role="group" aria-label="Suggested categories">
            <span className="hint">Start with:</span>
            {missing.map((s) => (
              <button
                key={s.path}
                type="button"
                title={s.description}
                onClick={() => {
                  created(addChannel.mutateAsync({ name: s.path, description: s.description }));
                }}
              >
                + {s.path}
              </button>
            ))}
          </div>
        )}
        <ul className="channels">
          {rows.map((row) => (
            <Category
              key={row.path}
              row={row}
              onSave={(text) => {
                attempt(updateChannel.mutateAsync({ name: row.path, description: text }));
              }}
              onDelete={() => {
                attempt(deleteChannel.mutateAsync(row.path));
              }}
            />
          ))}
        </ul>
        <form
          className="manage-form inline"
          aria-label="Add a category"
          onSubmit={(e) => {
            e.preventDefault();
            const path = parent ? `${parent}${SEP}${name}` : name;
            created(addChannel.mutateAsync({ name: path, description }), () => {
              setName("");
              setDescription("");
            });
          }}
        >
          <label>
            Inside
            <select
              value={parent}
              onChange={(e) => {
                setParent(e.target.value);
              }}
            >
              <option value="">(top level)</option>
              {rows
                .filter((r) => r.path !== "Other" && r.depth < 3)
                .map((r) => (
                  <option key={r.path} value={r.path}>
                    {r.path}
                  </option>
                ))}
            </select>
          </label>
          <label>
            New category
            <input
              value={name}
              onChange={(e) => {
                setName(e.target.value);
              }}
            />
          </label>
          <label>
            Description
            <input
              value={description}
              placeholder="helps the model choose"
              onChange={(e) => {
                setDescription(e.target.value);
              }}
            />
          </label>
          <button type="submit">Add category</button>
        </form>
      </section>

      <section aria-label="Existing items">
        <h2>Items already in your inbox</h2>
        <p className="hint">
          Categories apply to new items. To move what you already have: items from a source that feeds exactly one
          category go there at once; items the model left in Other, or in a category that now has subcategories, are
          read again at the next run.
        </p>
        <button
          type="button"
          onClick={() => {
            attempt(refile.mutateAsync());
          }}
        >
          File existing items again
        </button>
        {refile.data && (
          <p role="status">
            Filed {refile.data.filed} by rule. {refile.data.queued} will be read again by the model at the next run:
            press Run now to do it.
          </p>
        )}
      </section>
    </>
  );
}
