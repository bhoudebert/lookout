import { useState } from "react";
import type { Channel } from "../api/types";
import { useManage } from "../hooks";

const message = (error: unknown): string => (error as Error).message;

export function ChannelsPanel({ channels }: { channels: Channel[] }) {
  const { addChannel, updateChannel, deleteChannel } = useManage();
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [editing, setEditing] = useState<string | null>(null);
  const [draft, setDraft] = useState("");
  const [problem, setProblem] = useState<string | null>(null);

  /** Run one action; only the latest outcome is shown, so an old refusal never lingers. */
  const attempt = (action: Promise<unknown>, then?: () => void) => {
    setProblem(null);
    action.then(then, (error: unknown) => {
      setProblem(message(error));
    });
  };

  return (
    <section aria-label="Channels">
      <h2>Channels</h2>
      <p className="hint">
        The topics you look at. A source feeds one or more of them; the model files items among them.
      </p>
      {problem && (
        <p role="alert" className="form-error">
          {problem}
        </p>
      )}
      <ul className="channels">
        {channels.map((channel) => (
          <li key={channel.name}>
            <strong>{channel.name}</strong>
            {editing === channel.name ? (
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
                    attempt(updateChannel.mutateAsync({ name: channel.name, description: draft }), () => {
                      setEditing(null);
                    });
                  }}
                >
                  Save
                </button>
                <button
                  type="button"
                  onClick={() => {
                    setEditing(null);
                  }}
                >
                  Cancel
                </button>
              </>
            ) : (
              <>
                <span className="hint">{channel.description || "no description"}</span>
                <button
                  type="button"
                  aria-label={`Edit ${channel.name}`}
                  onClick={() => {
                    setEditing(channel.name);
                    setDraft(channel.description);
                  }}
                >
                  Edit
                </button>
                <button
                  type="button"
                  aria-label={`Delete ${channel.name}`}
                  onClick={() => {
                    attempt(deleteChannel.mutateAsync(channel.name));
                  }}
                >
                  Delete
                </button>
              </>
            )}
          </li>
        ))}
      </ul>
      <form
        className="manage-form inline"
        aria-label="Add a channel"
        onSubmit={(e) => {
          e.preventDefault();
          attempt(addChannel.mutateAsync({ name, description }), () => {
            setName("");
            setDescription("");
          });
        }}
      >
        <label>
          New channel
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
        <button type="submit">Add channel</button>
      </form>
    </section>
  );
}
