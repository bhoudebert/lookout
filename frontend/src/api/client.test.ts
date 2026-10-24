import { afterEach, describe, expect, it, vi } from "vitest";
import { NO_FILTERS } from "./types";
import { ApiError, api, itemsQuery } from "./client";

afterEach(() => {
  vi.unstubAllGlobals();
});

const answer = (status: number, body: unknown) =>
  vi.fn(() => Promise.resolve(new Response(typeof body === "string" ? body : JSON.stringify(body), { status })));

describe("itemsQuery", () => {
  it("writes every filter", () => {
    const query = itemsQuery({
      priorities: ["P0", "P1"],
      channel: "Dev > Rust",
      source: "hn",
      view: "done",
      starred: true,
      text: "django",
    });
    expect(query).toBe(
      "priority=P0&priority=P1&channel=Dev+%3E+Rust&source=hn&state=done&starred=true&text=django&limit=100",
    );
  });
  it("asks for a dry run when only previewing the filing", async () => {
    const fetch = answer(200, { filed: 0, queued: 0 });
    vi.stubGlobal("fetch", fetch);
    await api.refile(true);
    await api.refile();
    const urls = fetch.mock.calls.map((c) => (c as unknown as [string])[0]);
    expect(urls).toEqual(["/api/refile?dry_run=true", "/api/refile?dry_run=false"]);
  });
  it("writes nothing for the defaults", () => {
    expect(itemsQuery(NO_FILTERS, 10)).toBe("limit=10");
  });
  it("asks for every state in the everything view", () => {
    expect(itemsQuery({ ...NO_FILTERS, view: "all" })).toContain("state=snoozed");
  });
});

describe("api", () => {
  it("reads json and sends the content type", async () => {
    const fetch = answer(200, { items: [], total: 0 });
    vi.stubGlobal("fetch", fetch);
    expect(await api.items(NO_FILTERS)).toEqual({ items: [], total: 0 });
    const init = fetch.mock.calls[0] as unknown as [string, RequestInit];
    expect(new Headers(init[1].headers).get("Content-Type")).toBe("application/json");
  });

  it("turns a refusal into an ApiError carrying the detail", async () => {
    vi.stubGlobal("fetch", answer(409, { detail: "already in the inbox" }));
    await expect(api.act("x", "reopen")).rejects.toMatchObject({
      name: "ApiError",
      status: 409,
      message: "already in the inbox",
    });
  });

  it("falls back to the status when the body has no text detail", async () => {
    vi.stubGlobal("fetch", answer(422, { detail: [{ msg: "bad" }] }));
    await expect(api.item("x")).rejects.toThrow("Request failed (422)");
  });

  it("falls back to the status when the body is not json", async () => {
    vi.stubGlobal("fetch", answer(502, "<html>bad gateway</html>"));
    await expect(api.sources()).rejects.toThrow("Request failed (502)");
  });

  it("says Lookout cannot be reached when the network is down", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(() => Promise.reject(new TypeError("down"))),
    );
    const error = await api.runStatus().catch((e: unknown) => e);
    expect(error).toBeInstanceOf(ApiError);
    expect((error as ApiError).status).toBe(0);
    expect((error as ApiError).message).toMatch(/Cannot reach Lookout/);
  });

  it.each([
    [
      "restore",
      () => api.restore("a", { state: "new", snoozed_until: null, starred: false }),
      "POST",
      "/api/items/a/restore",
    ],
    ["bulk", () => api.bulk(["a", "b"], "done", undefined), "POST", "/api/items/bulk"],
    ["seenBelow", () => api.seenBelow("P1"), "POST", "/api/items/seen-below"],
    ["setSource", () => api.setSource("my blog", false), "PATCH", "/api/sources/my%20blog"],
    ["run", () => api.run(), "POST", "/api/run"],
  ])("%s uses %s %s", async (_name, call, method, path) => {
    const fetch = answer(200, {});
    vi.stubGlobal("fetch", fetch);
    await call();
    const [url, init] = fetch.mock.calls[0] as unknown as [string, RequestInit];
    expect([init.method, url]).toEqual([method, path]);
  });
});
