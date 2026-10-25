import type { DigestJob } from "../api/types";
import { useDigestJobs } from "../hooks";

/** What the header says about digests: the one being written, or the last that ended. Nothing when there is none. */
export function describe(job: DigestJob): string {
  if (job.state === "running") {
    const where = job.sections_total > 0 ? ` ${String(job.section_number)}/${String(job.sections_total)}` : "";
    return `Digest: writing${where}…`;
  }
  if (job.state === "done") return "Digest ready";
  if (job.state === "failed") return "Digest failed";
  return "Digest cancelled";
}

export function DigestStatus({ go }: { go: (path: string) => void }) {
  const jobs = useDigestJobs();
  const job = jobs.data?.[0];
  if (!job) return null;
  const path = job.state === "done" && job.digest_id ? `/digest/${job.digest_id}` : "/digest";
  return (
    <div className="digest-status" aria-live="polite">
      <a
        href={path}
        onClick={(e) => {
          e.preventDefault();
          go(path);
        }}
      >
        {describe(job)}
      </a>
    </div>
  );
}
