import { useState } from "react";
import type { Source, SourceBody, SourceField, SourceType } from "../api/types";

type Values = Record<string, string | boolean>;

interface Props {
  types: [SourceType, ...SourceType[]];
  channels: string[];
  /** The source being edited; absent when adding one. */
  source?: Source;
  error?: string;
  busy: boolean;
  onSave: (name: string, body: SourceBody) => void;
  onCancel: () => void;
}

const asText = (value: unknown): string =>
  typeof value === "string" || typeof value === "number" ? String(value) : "";

/** What a setting looks like in a form field. */
function show(field: SourceField, value: unknown): string | boolean {
  if (field.kind === "bool") return value === undefined ? field.default === true : value === true;
  if (field.kind === "list") {
    const entries = Array.isArray(value) ? value : Array.isArray(field.default) ? field.default : [];
    return entries.map(asText).join("\n");
  }
  return asText(value === undefined ? field.default : value);
}

function initial(type: SourceType, settings: Record<string, unknown>): Values {
  return Object.fromEntries(type.fields.map((f) => [f.name, show(f, settings[f.name])]));
}

/** What a form field becomes in the settings sent to the server. Blank optional settings are left out. */
function read(field: SourceField, value: string | boolean): unknown {
  if (field.kind === "bool") return value;
  const text = value as string;
  if (field.kind === "list")
    return text
      .split("\n")
      .map((l) => l.trim())
      .filter(Boolean);
  if (field.kind === "number") return text === "" ? undefined : Number(text);
  return text.trim();
}

export function SourceForm({ types, channels, source, error, busy, onSave, onCancel }: Props) {
  const [name, setName] = useState(source?.name ?? "");
  const [typeIndex, setTypeIndex] = useState(
    Math.max(
      0,
      types.findIndex((t) => t.name === source?.type),
    ),
  );
  const type = types[typeIndex] as SourceType;
  const [values, setValues] = useState<Values>(initial(type, source?.settings ?? {}));
  const [picked, setPicked] = useState<string[]>(source?.channels ?? []);
  const [keywords, setKeywords] = useState((source?.keywords ?? []).join(", "));
  const [enabled, setEnabled] = useState(source?.enabled ?? true);

  const changeType = (index: number) => {
    setTypeIndex(index);
    setValues(initial(types[index] as SourceType, {}));
  };
  const submit = () => {
    const settings: Record<string, unknown> = {};
    for (const field of type.fields) {
      const value = read(field, values[field.name] as string | boolean);
      if (value !== undefined) settings[field.name] = value;
    }
    onSave(name, {
      type: type.name,
      settings,
      channels: picked,
      keywords: keywords
        .split(",")
        .map((k) => k.trim())
        .filter(Boolean),
      enabled,
    });
  };

  return (
    <form
      className="manage-form"
      aria-label={source ? `Edit ${source.name}` : "Add a source"}
      onSubmit={(e) => {
        e.preventDefault();
        submit();
      }}
    >
      <h3>{source ? `Edit ${source.name}` : "Add a source"}</h3>
      <label>
        Name
        <input
          value={name}
          disabled={source !== undefined}
          onChange={(e) => {
            setName(e.target.value);
          }}
        />
      </label>
      <label>
        Type
        <select
          value={typeIndex}
          disabled={source !== undefined}
          onChange={(e) => {
            changeType(Number(e.target.value));
          }}
        >
          {types.map((t, index) => (
            <option key={t.name} value={index}>
              {t.label}
            </option>
          ))}
        </select>
      </label>
      <p className="hint">{type.description}</p>
      {type.fields.map((field) => {
        const id = `field-${field.name}`;
        const hint =
          field.help && field.kind !== "text" ? (
            <span id={`${id}-hint`} className="hint">
              {field.help}
            </span>
          ) : null;
        const describedBy = hint ? `${id}-hint` : undefined;
        if (field.kind === "bool") {
          return (
            <div key={field.name} className="field">
              <label className="check">
                <input
                  id={id}
                  type="checkbox"
                  aria-describedby={describedBy}
                  checked={values[field.name] === true}
                  onChange={(e) => {
                    setValues({ ...values, [field.name]: e.target.checked });
                  }}
                />
                {field.label}
              </label>
              {hint}
            </div>
          );
        }
        return (
          <div key={field.name} className="field">
            <label htmlFor={id}>{field.label}</label>
            {field.kind === "list" ? (
              <textarea
                id={id}
                rows={3}
                aria-describedby={describedBy}
                value={values[field.name] as string}
                onChange={(e) => {
                  setValues({ ...values, [field.name]: e.target.value });
                }}
              />
            ) : (
              <input
                id={id}
                type={field.kind === "number" ? "number" : "text"}
                aria-describedby={describedBy}
                value={values[field.name] as string}
                placeholder={field.help}
                onChange={(e) => {
                  setValues({ ...values, [field.name]: e.target.value });
                }}
              />
            )}
            {hint}
          </div>
        );
      })}
      <fieldset>
        <legend>Feeds these channels</legend>
        {channels.map((channel) => (
          <label key={channel} className="check">
            <input
              type="checkbox"
              checked={picked.includes(channel)}
              onChange={(e) => {
                setPicked(e.target.checked ? [...picked, channel] : picked.filter((c) => c !== channel));
              }}
            />
            {channel}
          </label>
        ))}
        <span className="hint">
          One channel files its items there directly. Several, or none, let the model choose among them.
        </span>
      </fieldset>
      <label>
        Keywords
        <input
          value={keywords}
          placeholder="only items mentioning one of these, comma separated"
          onChange={(e) => {
            setKeywords(e.target.value);
          }}
        />
      </label>
      <label className="check">
        <input
          type="checkbox"
          checked={enabled}
          onChange={(e) => {
            setEnabled(e.target.checked);
          }}
        />
        Enabled
      </label>
      {error && (
        <p role="alert" className="form-error">
          {error}
        </p>
      )}
      <div className="actions">
        <button type="submit" disabled={busy}>
          {source ? "Save" : "Add"}
        </button>
        <button type="button" onClick={onCancel}>
          Cancel
        </button>
      </div>
    </form>
  );
}
