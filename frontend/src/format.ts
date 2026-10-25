/** "5 min ago", "3 h ago", "2 d ago": coarse on purpose, an inbox does not need seconds. */
export function timeAgo(iso: string, now: Date): string {
  const minutes = Math.max(0, Math.round((now.getTime() - new Date(iso).getTime()) / 60000));
  if (minutes < 1) return "just now";
  if (minutes < 60) return `${minutes} min ago`;
  const hours = Math.round(minutes / 60);
  if (hours < 48) return `${hours} h ago`;
  return `${Math.round(hours / 24)} d ago`;
}

export function until(iso: string): string {
  return new Date(iso).toLocaleString(undefined, { dateStyle: "medium", timeStyle: "short" });
}

/** The address when it is a web page; anything else (javascript:, data:) must never become a link. */
export function webUrl(url: string): string | undefined {
  return /^https?:\/\/\S/i.test(url.trim()) ? url.trim() : undefined;
}
