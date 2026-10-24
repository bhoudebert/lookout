interface Props {
  kind: "loading" | "empty" | "error";
  message?: string;
  onRetry?: () => void;
}

/** The three states every screen shares (openspec: dashboard, "States of the screen"). */
export function StateView({ kind, message, onRetry }: Props) {
  if (kind === "loading")
    return (
      <p aria-busy="true" className="state">
        Loading…
      </p>
    );
  if (kind === "error") {
    return (
      <div role="alert" className="state error">
        <p>{message}</p>
        {onRetry && (
          <button type="button" onClick={onRetry}>
            Try again
          </button>
        )}
      </div>
    );
  }
  return <p className="state">{message}</p>;
}
