import { screen, waitFor, within } from "@testing-library/react";
import { beforeEach, describe, expect, it } from "vitest";
import { FakeBackend, makeItem } from "./test/fakeBackend";
import { mount } from "./test/render";

beforeEach(() => {
  window.localStorage.clear();
});

const news = () => [
  makeItem({ id: "a", title: "Quake in Chile", sources: ["wire"], url: "https://news.test/a" }),
  makeItem({ id: "b", title: "Chip maker merger", sources: ["tech"], url: "https://news.test/b" }),
  makeItem({ id: "c", title: "Local fair opens", sources: ["town"], url: "javascript:alert(1)" }),
];

/** The page of a digest, once the background job has written it. */
const digestPage = () => screen.findByRole("article", { name: "Digest" }, { timeout: 4000 });

describe("summarising a selection", () => {
  it("returns at once, says where the digest will appear, and shows it being written in the header", async () => {
    const backend = new FakeBackend(news());
    backend.digestHold = true;
    const { user } = mount(backend);
    await user.click(await screen.findByRole("button", { name: "Summarise these 3…" }));

    expect(
      await screen.findByText(/Writing the digest in the background: it will appear under Digest/),
    ).toBeInTheDocument();
    expect(window.location.pathname).toBe("/");
    const header = await screen.findByRole("link", { name: "Digest: writing…" });
    expect(header).toHaveAttribute("href", "/digest");
    expect(screen.getByRole("button", { name: /^Summarise these/ })).toBeDisabled();
    const calls = backend.calls.filter((c) => c.path === "/api/digests" && c.method === "POST");
    expect(calls[0]?.body).toMatchObject({ filter: { text: "", state: [] } });
  });

  it("follows the digest on the Digest page: the part, the tokens, and a way to cancel", async () => {
    const backend = new FakeBackend(news());
    backend.digestHold = true;
    const { user } = mount(backend);
    await user.click(await screen.findByRole("button", { name: /^Summarise these/ }));
    await user.click(await screen.findByRole("link", { name: "Digest: writing…" }));

    const rows = await screen.findByRole("list", { name: "Being written" });
    expect(within(rows).getByText("Writing")).toBeInTheDocument();
    expect(rows).toHaveTextContent("getting ready");

    const job = backend.digestJobs[0] as (typeof backend.digestJobs)[number];
    Object.assign(job, { section: "Dev", section_number: 1, sections_total: 3, tokens: 412 });
    await waitFor(
      () => {
        expect(rows).toHaveTextContent("Dev (1 of 3) · about 412 tokens written");
      },
      { timeout: 3000 },
    );
    expect(await screen.findByRole("link", { name: "Digest: writing 1/3…" })).toBeInTheDocument();

    await user.click(within(rows).getByRole("button", { name: "Cancel" }));
    expect(await within(rows).findByText("Cancelled")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Digest cancelled" })).toBeInTheDocument();
    await user.click(within(rows).getByRole("button", { name: "Dismiss Inbox" }));
    await waitFor(() => {
      expect(screen.queryByRole("list", { name: "Being written" })).not.toBeInTheDocument();
    });
  });

  it("keeps writing when the user goes elsewhere, and offers the finished digest in the header", async () => {
    const backend = new FakeBackend(news());
    backend.digestHold = true;
    const { user } = mount(backend);
    await user.click(await screen.findByRole("button", { name: /^Summarise these/ }));
    await user.click(await screen.findByRole("link", { name: "Categories" }));
    expect(await screen.findByRole("link", { name: "Digest: writing…" })).toBeInTheDocument();

    backend.digestHold = false;
    const ready = await screen.findByRole("link", { name: "Digest ready" }, { timeout: 4000 });
    expect(ready).toHaveAttribute("href", "/digest/d1");
    await user.click(ready);
    const digest = await digestPage();
    expect(within(digest).getByText("Today: a security fix and a release.")).toBeInTheDocument();
    expect(window.location.pathname).toBe("/digest/d1");
  });

  it("says a digest is already being written instead of starting a second one", async () => {
    const backend = new FakeBackend(news());
    backend.digestHold = true;
    const { user } = mount(backend, "/digest");
    expect(await screen.findByText(/None yet/)).toBeInTheDocument();
    backend.digestJobs.push({
      id: "jx",
      scope: "Inbox",
      started_at: "2026-10-24T08:00:00Z",
      state: "running",
      section: "",
      section_number: 0,
      sections_total: 0,
      tokens: 0,
      finished_at: null,
      error: null,
      digest_id: null,
      started: false,
    });
    await user.click(screen.getByRole("link", { name: "Inbox" }));
    expect(await screen.findByRole("button", { name: /^Summarise these/ })).toBeDisabled();
    expect(backend.calls.filter((c) => c.path === "/api/digests" && c.method === "POST")).toHaveLength(0);
  });

  it("keeps a failure in the list with its reason until dismissed", async () => {
    const backend = new FakeBackend(news());
    backend.digestFails = "the model did not stop writing: it reached the limit of 6144 tokens";
    const { user } = mount(backend);
    await user.click(await screen.findByRole("button", { name: /^Summarise these/ }));
    expect(await screen.findByRole("link", { name: "Digest failed" }, { timeout: 4000 })).toBeInTheDocument();
    await user.click(screen.getByRole("link", { name: "Digest failed" }));

    const rows = await screen.findByRole("list", { name: "Being written" });
    expect(rows).toHaveTextContent("Failed");
    expect(rows).toHaveTextContent("it reached the limit of 6144 tokens");
    await user.click(within(rows).getByRole("button", { name: "Dismiss Inbox" }));
    await waitFor(() => {
      expect(screen.queryByRole("list", { name: "Being written" })).not.toBeInTheDocument();
    });
    expect(screen.queryByRole("link", { name: "Digest failed" })).not.toBeInTheDocument();
  });

  it("says why when the request itself is refused", async () => {
    const backend = new FakeBackend(news());
    const { user } = mount(backend);
    await screen.findByRole("button", { name: /^Summarise these/ });
    backend.failWith = { status: 500, detail: "disk is full" };
    await user.click(screen.getByRole("button", { name: /^Summarise these/ }));
    expect(await screen.findByText(/disk is full/)).toBeInTheDocument();
    expect(window.location.pathname).toBe("/");
  });

  it("offers nothing to summarise on an empty selection", async () => {
    mount(new FakeBackend([]));
    await screen.findByText(/Nothing to look at/);
    expect(screen.queryByRole("button", { name: /^Summarise these/ })).not.toBeInTheDocument();
  });
});

describe("reading digests", () => {
  /** A digest, written through the whole flow, open on its page. */
  const written = async () => {
    const backend = new FakeBackend(news());
    const view = mount(backend);
    await view.user.click(await screen.findByRole("button", { name: /^Summarise these/ }));
    await view.user.click(await screen.findByRole("link", { name: "Digest ready" }, { timeout: 4000 }));
    await digestPage();
    return { backend, ...view };
  };

  it("shows the headline, the sections with their sources, and what was not covered", async () => {
    const { user } = await written();
    const digest = screen.getByRole("article", { name: "Digest" });
    expect(within(digest).getByText("Today: a security fix and a release.")).toBeInTheDocument();
    expect(
      within(digest)
        .getByText(/All digests/)
        .closest("p"),
    ).toHaveTextContent(/Inbox · .* · 3 of 3 items/);
    const dev = within(digest).getByRole("region", { name: "Dev" });
    expect(within(dev).getByRole("link", { name: "Quake in Chile" })).toHaveAttribute("href", "https://news.test/a");
    expect(within(dev).getByRole("link", { name: "Quake in Chile" })).toHaveAttribute("target", "_blank");
    await user.click(within(digest).getByText("1 not covered"));
    expect(within(digest).queryByRole("link", { name: "Local fair opens" })).not.toBeInTheDocument();
    expect(within(digest).getByText("town")).toHaveAttribute("title", "Local fair opens");
  });

  it("marks the cited items done in one action, leaving the digest readable", async () => {
    const { user, backend } = await written();
    await user.click(screen.getByRole("button", { name: "Mark the 2 cited items done" }));
    expect(await screen.findByText("2 items marked done.")).toBeInTheDocument();
    expect(backend.calls.find((c) => c.path === "/api/items/bulk")?.body).toEqual({ ids: ["a", "b"], action: "done" });
    expect(await screen.findByRole("button", { name: "Nothing left to mark done" })).toBeDisabled();
    expect(screen.getByRole("region", { name: "Dev" })).toBeInTheDocument();
  });

  it("shows why a bulk action was refused", async () => {
    const { user, backend } = await written();
    backend.failWith = { status: 409, detail: "cannot do that" };
    await user.click(screen.getByRole("button", { name: "Mark the 2 cited items done" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("cannot do that");
  });

  it("shows why a digest could not be deleted, and keeps it", async () => {
    const { user, backend } = await written();
    backend.failWith = { status: 500, detail: "disk is full" };
    await user.click(screen.getByRole("button", { name: "Delete this digest" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("disk is full");
    expect(screen.getByRole("article", { name: "Digest" })).toBeInTheDocument();
  });

  it("lists the digests kept and the finished attempt, opens one from either, and deletes it", async () => {
    const { user } = await written();
    await user.click(screen.getByRole("link", { name: "All digests" }));
    const list = await screen.findByRole("region", { name: "Digests" });
    const rows = within(list).getByRole("list", { name: "Being written" });
    expect(rows).toHaveTextContent("Ready");
    await user.click(within(rows).getByRole("button", { name: "Open" }));
    await digestPage();
    expect(window.location.pathname).toBe("/digest/d1");

    await user.click(screen.getByRole("link", { name: "All digests" }));
    await user.click(await screen.findByRole("button", { name: "Today: a security fix and a release." }));
    await digestPage();
    await user.click(screen.getByRole("button", { name: "Delete this digest" }));
    expect(await screen.findByRole("region", { name: "Digests" })).toBeInTheDocument();
    expect(window.location.pathname).toBe("/digest");
    expect(screen.queryByRole("button", { name: "Today: a security fix and a release." })).not.toBeInTheDocument();
  });

  it("explains how to make a first digest", async () => {
    mount(new FakeBackend(news()), "/digest");
    expect(await screen.findByText(/None yet/)).toBeInTheDocument();
  });

  it("shows an error for a digest that does not exist, and can retry", async () => {
    const { user } = mount(new FakeBackend(news()), "/digest/zzz");
    expect(await screen.findByText(/no digest zzz/)).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Try again" }));
    await waitFor(() => {
      expect(screen.getByText(/no digest zzz/)).toBeInTheDocument();
    });
  });

  it("shows an error when the list cannot be loaded, and can retry", async () => {
    const backend = new FakeBackend(news());
    backend.failOn = "/api/digests";
    const { user } = mount(backend, "/digest");
    expect(await screen.findByText(/broken/)).toBeInTheDocument();
    backend.failOn = null;
    await user.click(screen.getByRole("button", { name: "Try again" }));
    expect(await screen.findByText(/None yet/)).toBeInTheDocument();
  });

  it("is reached from the menu", async () => {
    const { user } = mount(new FakeBackend(news()));
    await user.click(await screen.findByRole("link", { name: "Digest" }));
    expect(await screen.findByRole("region", { name: "Digests" })).toBeInTheDocument();
  });
});
