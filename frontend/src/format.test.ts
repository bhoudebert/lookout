import { timeAgo, until } from "./format";

const now = new Date("2026-10-24T12:00:00Z");

describe("timeAgo", () => {
  it.each([
    ["2026-10-24T12:00:00Z", "just now"],
    ["2026-10-24T12:30:00Z", "just now"],
    ["2026-10-24T11:55:00Z", "5 min ago"],
    ["2026-10-24T09:00:00Z", "3 h ago"],
    ["2026-10-22T12:00:00Z", "2 d ago"],
  ])("%s is %s", (iso, text) => {
    expect(timeAgo(iso, now)).toBe(text);
  });
});

describe("until", () => {
  it("writes a date and time", () => {
    expect(until("2026-10-25T09:00:00Z")).toMatch(/2026/);
  });
});
