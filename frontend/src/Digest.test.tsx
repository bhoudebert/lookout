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

describe("summarising a selection", () => {
  it("writes a digest of what the inbox shows, says it is working, and opens it", async () => {
    const backend = new FakeBackend(news());
    let finish = () => {};
    backend.digestGate = new Promise((resolve) => {
      finish = resolve;
    });
    const { user } = mount(backend);
    await user.click(await screen.findByRole("button", { name: "Summarise these 3…" }));
    expect(await screen.findByText(/Writing the digest/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Summarise these 3…" })).toBeDisabled();
    finish();
    const digest = await screen.findByRole("article", { name: "Digest" });
    expect(window.location.pathname).toBe("/digest/d1");
    expect(within(digest).getByText("Today: a security fix and a release.")).toBeInTheDocument();
    expect(
      within(digest)
        .getByText(/All digests/)
        .closest("p"),
    ).toHaveTextContent(/Inbox · .* · 3 of 3 items/);
    const dev = within(digest).getByRole("region", { name: "Dev" });
    expect(within(dev).getByRole("link", { name: "Quake in Chile" })).toHaveAttribute("href", "https://news.test/a");
    expect(within(dev).getByRole("link", { name: "Quake in Chile" })).toHaveAttribute("target", "_blank");
    const calls = backend.calls.filter((c) => c.path === "/api/digests" && c.method === "POST");
    expect(calls[0]?.body).toMatchObject({ filter: { text: "", state: [] } });
  });

  it("lists what the model did not cover and never links an address that is not a web page", async () => {
    const { user } = mount(new FakeBackend([...news(), makeItem({ id: "d", title: "Odd", url: "javascript:x" })]));
    await user.click(await screen.findByRole("button", { name: /^Summarise these/ }));
    const digest = await screen.findByRole("article", { name: "Digest" });
    await user.click(within(digest).getByText("2 not covered"));
    expect(within(digest).queryByRole("link", { name: "Odd" })).not.toBeInTheDocument();
    expect(within(digest).getByText("Odd")).toBeInTheDocument();
    expect(within(digest).getByText("town")).toHaveAttribute("title", "Local fair opens");
  });

  it("says why when the model could not write it, and stays on the inbox", async () => {
    const backend = new FakeBackend(news());
    backend.digestFails = "the model could not write the digest: it is down";
    const { user } = mount(backend);
    await user.click(await screen.findByRole("button", { name: /^Summarise these/ }));
    expect(await screen.findByText(/the model could not write the digest: it is down/)).toBeInTheDocument();
    expect(window.location.pathname).toBe("/");
    expect(screen.getByRole("button", { name: /^Summarise these/ })).toBeEnabled();
  });

  it("offers nothing to summarise on an empty selection", async () => {
    mount(new FakeBackend([]));
    await screen.findByText(/Nothing here/i, undefined, { timeout: 2000 }).catch(() => undefined);
    expect(screen.queryByRole("button", { name: /^Summarise these/ })).not.toBeInTheDocument();
  });
});

describe("reading digests", () => {
  const written = async () => {
    const backend = new FakeBackend(news());
    const view = mount(backend);
    await view.user.click(await screen.findByRole("button", { name: /^Summarise these/ }));
    await screen.findByRole("article", { name: "Digest" });
    return { backend, ...view };
  };

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

  it("lists the digests kept, opens one, and deletes it", async () => {
    const { user } = await written();
    await user.click(screen.getByRole("link", { name: "All digests" }));
    const list = await screen.findByRole("region", { name: "Digests" });
    await user.click(within(list).getByRole("button", { name: "Today: a security fix and a release." }));
    await screen.findByRole("article", { name: "Digest" });
    expect(window.location.pathname).toBe("/digest/d1");

    await user.click(screen.getByRole("button", { name: "Delete this digest" }));
    expect(await screen.findByText(/None yet/)).toBeInTheDocument();
    expect(window.location.pathname).toBe("/digest");
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
