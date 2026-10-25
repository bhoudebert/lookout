import { useMemo } from "react";
import type { Digest, DigestItem, DigestJob } from "../api/types";
import { timeAgo, webUrl } from "../format";
import {
  useBulk,
  useCancelDigestJob,
  useDeleteDigest,
  useDigest,
  useDigestJobs,
  useDigests,
  useDismissDigestJob,
} from "../hooks";
import { StateView } from "./StateView";

const message = (error: unknown): string => (error as Error).message;

/** Where a cited item can be read: a link when it has a web address, plain text when it does not. */
function Source({ item }: { item: DigestItem }) {
  const href = webUrl(item.url);
  const name = item.sources[0] as string;
  return href ? (
    <a href={href} target="_blank" rel="noreferrer noopener" aria-label={item.title} title={item.title}>
      {name}
    </a>
  ) : (
    <span title={item.title}>{name}</span>
  );
}

function DigestPage({ digest, onClose }: { digest: Digest; onClose: () => void }) {
  const bulk = useBulk();
  const remove = useDeleteDigest(onClose);
  // Only what is still waiting in the inbox can be marked done; parked and finished items are left alone.
  const waiting = useMemo(() => {
    const byId = new Map<string, DigestItem>();
    for (const section of digest.sections)
      for (const point of section.points) for (const item of point.items) byId.set(item.id, item);
    return [...byId.values()].filter((i) => i.state === "new" || i.state === "seen").map((i) => i.id);
  }, [digest]);
  return (
    <article className="digest" aria-label="Digest">
      <p className="hint">
        <a
          href="/digest"
          onClick={(e) => {
            e.preventDefault();
            onClose();
          }}
        >
          All digests
        </a>
        {" · "}
        {digest.scope} · {timeAgo(digest.created_at, new Date())} · {digest.count} of {digest.total} items
      </p>
      <p className="headline">{digest.headline}</p>
      {digest.sections.map((section) => (
        <section key={section.title} aria-label={section.title}>
          <h3>{section.title}</h3>
          <ul>
            {section.points.map((point) => (
              <li key={point.text}>
                {point.text}{" "}
                <span className="sources">
                  {point.items.map((item) => (
                    <Source key={item.id} item={item} />
                  ))}
                </span>
              </li>
            ))}
          </ul>
        </section>
      ))}
      {digest.uncovered.length > 0 && (
        <details>
          <summary>{digest.uncovered.length} not covered</summary>
          <ul>
            {digest.uncovered.map((item) => (
              <li key={item.id}>
                {item.title} <Source item={item} />
              </li>
            ))}
          </ul>
        </details>
      )}
      {(bulk.isError || remove.isError) && (
        <p role="alert" className="form-error">
          {message(bulk.error ?? remove.error)}
        </p>
      )}
      <p className="actions">
        <button
          type="button"
          disabled={waiting.length === 0 || bulk.isPending}
          onClick={() => {
            bulk.mutate({ ids: waiting, action: "done" });
          }}
        >
          {waiting.length > 0 ? `Mark the ${waiting.length} cited items done` : "Nothing left to mark done"}
        </button>
        <button
          type="button"
          onClick={() => {
            remove.mutate(digest.id);
          }}
        >
          Delete this digest
        </button>
      </p>
      {bulk.isSuccess && <p role="status">{bulk.data.changed} items marked done.</p>}
    </article>
  );
}

/** One digest being written, or how an attempt ended, with what can be done about it. */
function Job({ job, onOpen }: { job: DigestJob; onOpen: (id: string) => void }) {
  const cancel = useCancelDigestJob();
  const dismiss = useDismissDigestJob();
  const when = timeAgo(job.started_at, new Date());
  const progress =
    job.sections_total > 0
      ? `${job.section} (${String(job.section_number)} of ${String(job.sections_total)})`
      : "getting ready";
  return (
    <li className={`job ${job.state}`}>
      {job.state === "running" && (
        <>
          <strong>Writing</strong> {job.scope}
          <span className="hint">
            {progress} · about {job.tokens} tokens written · started {when}
          </span>
          <button
            type="button"
            disabled={cancel.isPending}
            onClick={() => {
              cancel.mutate(job.id);
            }}
          >
            Cancel
          </button>
        </>
      )}
      {job.state === "done" && (
        <>
          <strong>Ready</strong> {job.scope}
          <span className="hint">started {when}</span>
          {job.digest_id && (
            <button
              type="button"
              onClick={() => {
                onOpen(job.digest_id as string);
              }}
            >
              Open
            </button>
          )}
        </>
      )}
      {job.state === "failed" && (
        <>
          <strong>Failed</strong> {job.scope}
          <span className="hint form-error">{job.error}</span>
        </>
      )}
      {job.state === "cancelled" && (
        <>
          <strong>Cancelled</strong> {job.scope}
          <span className="hint">started {when}</span>
        </>
      )}
      {job.state !== "running" && (
        <button
          type="button"
          aria-label={`Dismiss ${job.scope}`}
          onClick={() => {
            dismiss.mutate(job.id);
          }}
        >
          Dismiss
        </button>
      )}
    </li>
  );
}

/** One digest, or the list of the ones kept. */
export function DigestView({ id, onOpen }: { id: string | null; onOpen: (id: string | null) => void }) {
  const one = useDigest(id ?? "");
  const all = useDigests();
  const jobs = useDigestJobs();
  if (id) {
    if (one.isPending) return <StateView kind="loading" />;
    if (one.isError) {
      return (
        <StateView
          kind="error"
          message={message(one.error)}
          onRetry={() => {
            void one.refetch();
          }}
        />
      );
    }
    return (
      <DigestPage
        digest={one.data}
        onClose={() => {
          onOpen(null);
        }}
      />
    );
  }
  if (all.isPending) return <StateView kind="loading" />;
  if (all.isError) {
    return (
      <StateView
        kind="error"
        message={message(all.error)}
        onRetry={() => {
          void all.refetch();
        }}
      />
    );
  }
  return (
    <section aria-label="Digests">
      <h2>Digests</h2>
      {jobs.data && jobs.data.length > 0 && (
        <ul className="jobs" aria-label="Being written">
          {jobs.data.map((job) => (
            <Job key={job.id} job={job} onOpen={onOpen} />
          ))}
        </ul>
      )}
      {all.data.length === 0 && !jobs.data?.length ? (
        <p className="hint">
          None yet. In the inbox, narrow what you want to read (a category, the last day...) and click{" "}
          <em>Summarise these</em>: the model condenses it into a few cited lines per category.
        </p>
      ) : (
        <ul className="digests">
          {all.data.map((d) => (
            <li key={d.id}>
              <button
                type="button"
                onClick={() => {
                  onOpen(d.id);
                }}
              >
                {d.headline}
              </button>
              <span className="hint">
                {d.scope} · {timeAgo(d.created_at, new Date())} · {d.count} of {d.total} items
              </span>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
