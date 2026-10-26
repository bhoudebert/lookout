import { useMemo, useState } from "react";
import type { Digest, DigestItem, DigestJob, DigestSummary } from "../api/types";
import { span, timeAgo, until, webUrl } from "../format";
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

const SORTS = {
  written_desc: "Written, newest first",
  written_asc: "Written, oldest first",
  items_desc: "Newest items first",
  size_desc: "Most items first",
} as const;
type Sort = keyof typeof SORTS;

const time = (iso: string | null | undefined): number => (iso ? new Date(iso).getTime() : 0);

/** The digests in the order asked for; those kept before the dates were known go last when sorting by items. */
function sorted(digests: DigestSummary[], by: Sort): DigestSummary[] {
  const order: Record<Sort, (a: DigestSummary, b: DigestSummary) => number> = {
    written_desc: (a, b) => time(b.created_at) - time(a.created_at),
    written_asc: (a, b) => time(a.created_at) - time(b.created_at),
    items_desc: (a, b) => time(b.until) - time(a.until),
    size_desc: (a, b) => b.count - a.count,
  };
  return [...digests].sort(order[by]);
}

/** What a digest is made of: how many items, published when. */
function made(count: number, total: number, since?: string | null, to?: string | null): string {
  const days = span(since, to);
  return `${String(count)} of ${String(total)} items${days ? ` published ${days}` : ""}`;
}

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
        {digest.scope} · written {until(digest.created_at)} ·{" "}
        {made(digest.count, digest.total, digest.since, digest.until)}
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

/** One digest being written, or an attempt that did not end well, with what can be done about it. */
function Job({ job }: { job: DigestJob }) {
  const cancel = useCancelDigestJob();
  const dismiss = useDismissDigestJob();
  const when = timeAgo(job.started_at, new Date());
  const days = span(job.since, job.until);
  const covers = job.count > 0 ? `${String(job.count)} items${days ? ` published ${days}` : ""}` : "";
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
            {covers ? `${covers} · ` : ""}
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
      {job.state === "failed" && (
        <>
          <strong>Failed</strong> {job.scope}
          <span className="hint">
            {covers ? `${covers} · ` : ""}started {when}
          </span>
          <span className="hint form-error">{job.error}</span>
        </>
      )}
      {job.state === "cancelled" && (
        <>
          <strong>Cancelled</strong> {job.scope}
          <span className="hint">
            {covers ? `${covers} · ` : ""}started {when}
          </span>
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
  const [by, setBy] = useState<Sort>("written_desc");
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
  // A finished job is already in the list of digests: only what is being written or went wrong is shown here.
  const pending = (jobs.data ?? []).filter((j) => j.state !== "done");
  return (
    <section aria-label="Digests">
      <h1>Digests</h1>
      {pending.length > 0 && (
        <ul className="jobs" aria-label="Being written">
          {pending.map((job) => (
            <Job key={job.id} job={job} />
          ))}
        </ul>
      )}
      {all.data.length === 0 && pending.length === 0 ? (
        <p className="hint">
          None yet. In the inbox, narrow what you want to read (a category, the last day...) and click{" "}
          <em>Summarise these</em>: the model condenses it into a few cited lines per category.
        </p>
      ) : (
        all.data.length > 0 && (
          <>
            <label className="sort">
              Sort{" "}
              <select
                value={by}
                onChange={(e) => {
                  setBy(e.target.value as Sort);
                }}
              >
                {Object.entries(SORTS).map(([value, label]) => (
                  <option key={value} value={value}>
                    {label}
                  </option>
                ))}
              </select>
            </label>
            <ul className="digests" aria-label="Written">
              {sorted(all.data, by).map((d) => (
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
                    {d.scope} · written {until(d.created_at)} · {made(d.count, d.total, d.since, d.until)}
                  </span>
                </li>
              ))}
            </ul>
          </>
        )
      )}
    </section>
  );
}
