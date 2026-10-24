import { useState } from "react";
import type { Channel } from "../api/types";
import { useManage, useTaxonomy } from "../hooks";
import { StateView } from "./StateView";

const message = (error: unknown): string => (error as Error).message;

/** Starting points for someone whose only category is Other. One click adds one. */
const SUGGESTIONS: { name: string; description: string }[] = [
  { name: "AI", description: "Models, agents and the tooling around them" },
  { name: "Rust", description: "The Rust language and its ecosystem" },
  { name: "Security", description: "Vulnerabilities, advisories and fixes in what I run" },
  { name: "Web", description: "Browsers, frontend frameworks and the web platform" },
  { name: "Languages", description: "Python and other languages I write" },
  { name: "Cloud", description: "Infrastructure, containers and hosting" },
  { name: "Data", description: "Databases, data engineering and analytics" },
];

function Category({
  channel,
  onSave,
  onDelete,
}: {
  channel: Channel;
  onSave: (description: string) => void;
  onDelete: () => void;
}) {
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState(channel.description);
  const feeders = channel.sources ?? [];
  return (
    <li>
      <strong>{channel.name}</strong>
      <span className="count">{channel.items} items</span>
      {editing ? (
        <>
          <input
            aria-label={`Description of ${channel.name}`}
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
          <span className="hint">{channel.description || "no description: it helps the model choose"}</span>
          <button
            type="button"
            aria-label={`Edit ${channel.name}`}
            onClick={() => {
              setDraft(channel.description);
              setEditing(true);
            }}
          >
            Edit
          </button>
          <button type="button" aria-label={`Delete ${channel.name}`} onClick={onDelete}>
            Delete
          </button>
        </>
      )}
      <span className="hint feeders">
        {feeders.length > 0 ? `fed by ${feeders.join(", ")}` : "any source may file items here"}
      </span>
    </li>
  );
}

/** Categories (channels) and kinds: what you look at, and what an item is. ADR 0012 and 0014. */
export function CategoriesView() {
  const taxonomy = useTaxonomy();
  const { addChannel, updateChannel, deleteChannel, addKind, deleteKind, refile } = useManage();
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [kind, setKind] = useState("");
  const [problem, setProblem] = useState<string | null>(null);

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
  const { channels, kinds } = taxonomy.data;
  const missing = SUGGESTIONS.filter((s) => !channels.some((c) => c.name.toLowerCase() === s.name.toLowerCase()));

  /** Run one action; only the latest outcome is shown, so an old refusal never lingers. */
  const attempt = (action: Promise<unknown>, then?: () => void) => {
    setProblem(null);
    action.then(then, (error: unknown) => {
      setProblem(message(error));
    });
  };

  return (
    <>
      <section aria-label="Categories">
        <h2>Categories</h2>
        <p className="hint">
          The topics you look at. A source files its items in the categories you tick for it, or lets the model choose;
          the model picks the most specific category that fits and uses Other only as a last resort.
        </p>
        {problem && (
          <p role="alert" className="form-error">
            {problem}
          </p>
        )}
        {missing.length > 0 && (
          <div className="suggestions" role="group" aria-label="Suggested categories">
            <span className="hint">Start with:</span>
            {missing.map((s) => (
              <button
                key={s.name}
                type="button"
                title={s.description}
                onClick={() => {
                  attempt(addChannel.mutateAsync({ name: s.name, description: s.description }));
                }}
              >
                + {s.name}
              </button>
            ))}
          </div>
        )}
        <ul className="channels">
          {channels.map((channel) => (
            <Category
              key={channel.name}
              channel={channel}
              onSave={(text) => {
                attempt(updateChannel.mutateAsync({ name: channel.name, description: text }));
              }}
              onDelete={() => {
                attempt(deleteChannel.mutateAsync(channel.name));
              }}
            />
          ))}
        </ul>
        <form
          className="manage-form inline"
          aria-label="Add a category"
          onSubmit={(e) => {
            e.preventDefault();
            attempt(addChannel.mutateAsync({ name, description }), () => {
              setName("");
              setDescription("");
            });
          }}
        >
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
          category go there at once; items the model left in Other are read again at the next run.
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

      <section aria-label="Kinds">
        <h2>Kinds</h2>
        <p className="hint">What an item is. The model picks exactly one for each.</p>
        <ul className="kinds">
          {kinds.map((k) => (
            <li key={k}>
              {k}
              {k !== "other" && (
                <button
                  type="button"
                  aria-label={`Delete kind ${k}`}
                  onClick={() => {
                    attempt(deleteKind.mutateAsync(k));
                  }}
                >
                  ×
                </button>
              )}
            </li>
          ))}
        </ul>
        <form
          className="manage-form inline"
          aria-label="Add a kind"
          onSubmit={(e) => {
            e.preventDefault();
            attempt(addKind.mutateAsync(kind), () => {
              setKind("");
            });
          }}
        >
          <label>
            New kind
            <input
              value={kind}
              onChange={(e) => {
                setKind(e.target.value);
              }}
            />
          </label>
          <button type="submit">Add kind</button>
        </form>
      </section>
    </>
  );
}
