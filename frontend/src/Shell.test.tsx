import { screen, waitFor, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { markOf } from "./components/SourceMark";
import { FakeBackend, makeItem } from "./test/fakeBackend";
import { mount } from "./test/render";

const urgent = (id: string, title: string) =>
  makeItem({ id, title, priority: "P0", priority_label: "act today", channel: "Other" });

describe("the frame", () => {
  it("counts the inbox and the sources beside the screens, and keeps the count out of their names", async () => {
    mount(new FakeBackend([makeItem({ id: "a", title: "One" }), makeItem({ id: "b", title: "Two" })]));
    const inbox = await screen.findByRole("link", { name: "Inbox" });
    await waitFor(() => {
      expect(inbox).toHaveTextContent("2");
    });
    expect(screen.getByRole("link", { name: "Sources" })).toHaveTextContent("1");
    expect(screen.getByRole("link", { name: "Categories" })).not.toHaveTextContent(/\d/);
    expect(screen.getByRole("tab", { name: "Inbox" })).toHaveTextContent("2");
  });

  it("searches from the top bar, and the slash key goes there", async () => {
    const { user } = mount(
      new FakeBackend([makeItem({ id: "a", title: "Django flaw" }), makeItem({ id: "b", title: "Rust reader" })]),
    );
    await screen.findByRole("button", { name: "Django flaw" });
    const search = screen.getByLabelText("Search items, sources, tags");
    await user.keyboard("/");
    expect(search).toHaveFocus();
    await user.type(search, "rust");
    await waitFor(() => {
      expect(screen.queryByRole("button", { name: "Django flaw" })).not.toBeInTheDocument();
    });
    expect(window.location.search).toContain("q=rust");
    expect(screen.getByLabelText("Search")).toHaveValue("rust");
  });
});

describe("the foot of the sidebar", () => {
  it("says when there was no run, then when the last one finished, or that one is going or failed", async () => {
    const idle = new FakeBackend([]);
    const first = mount(idle);
    expect(await screen.findByText("No run yet")).toBeInTheDocument();
    first.unmount();

    const done = new FakeBackend([]);
    done.run = { ...done.run, finished_at: "2026-10-24T09:00:00Z" };
    const second = mount(done);
    expect(await screen.findByText(/^Last run \d\d:\d\d/)).toBeInTheDocument();
    second.unmount();

    const going = new FakeBackend([]);
    going.run = { ...going.run, running: true };
    const third = mount(going);
    expect(await screen.findByText("Running now")).toBeInTheDocument();
    third.unmount();

    const failed = new FakeBackend([]);
    failed.run = { ...failed.run, error: "disk full", finished_at: "2026-10-24T09:00:00Z" };
    mount(failed);
    expect(await screen.findByText("The last run failed")).toBeInTheDocument();
  });
});

describe("the line under the title", () => {
  it("names what needs action today, in the singular and the plural, and says nothing when nothing does", async () => {
    const one = mount(new FakeBackend([urgent("a", "Django flaw"), makeItem({ id: "b", title: "Calm" })]));
    expect(await screen.findByText("1 needs action today:")).toBeInTheDocument();
    expect(screen.getByText("Django flaw", { selector: ".finding" })).toBeInTheDocument();
    one.unmount();

    const two = mount(new FakeBackend([urgent("a", "Django flaw"), urgent("b", "Brotli flaw")]));
    expect(await screen.findByText("2 need action today:")).toBeInTheDocument();
    two.unmount();

    mount(new FakeBackend([makeItem({ id: "c", title: "Calm" })]));
    await screen.findByRole("button", { name: "Calm" });
    expect(document.querySelector(".finding")).toBeNull();
  });
});

describe("the marks of the sources", () => {
  it("takes initials from the name and a hue that stays the same for the same name", () => {
    expect(markOf("hacker-news")).toEqual({ initials: "Hn", hue: markOf("hacker-news").hue });
    expect(markOf("osv").initials).toBe("Os");
    expect(markOf("osv").hue).toBe(markOf("osv").hue);
    expect(markOf("---").initials).toBe("?");
  });

  it("falls back to the category when an item names no source", async () => {
    mount(new FakeBackend([makeItem({ id: "a", title: "Orphan", sources: [], channel: "Other" })]));
    const row = (await screen.findByRole("button", { name: "Orphan" })).closest("li") as HTMLElement;
    expect(within(row).getByText("Ot")).toBeInTheDocument();
  });
});

describe("the actions menu", () => {
  it("closes once an action is chosen", async () => {
    const { user } = mount(new FakeBackend([makeItem({ id: "a", title: "One" })]));
    await screen.findByRole("button", { name: "One" });
    const menu = document.querySelector("details.menu") as HTMLDetailsElement;
    await user.click(screen.getByText("Actions"));
    expect(menu.open).toBe(true);
    await user.click(screen.getByRole("button", { name: "Shortcuts" }));
    expect(menu.open).toBe(false);
    expect(await screen.findByRole("dialog")).toBeInTheDocument();
  });
});
