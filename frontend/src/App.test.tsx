import { act, fireEvent, screen, waitFor, within } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { FakeBackend, makeItem, makeSource } from "./test/fakeBackend";
import { mount } from "./test/render";

afterEach(() => {
  vi.unstubAllGlobals();
  vi.useRealTimers();
});

const three = () => [
  makeItem({
    id: "a",
    title: "Django flaw",
    priority: "P0",
    priority_label: "act today",
    channel: "AI",
    author: "Jane Doe",
    feed_tags: ["django"],
    tags: ["sql"],
    starred: true,
    stack_matches: ["django"],
    action_needed: true,
  }),
  makeItem({
    id: "b",
    title: "React 20 RC",
    priority: "P1",
    channel: "AI",
    sources: ["react-blog", "hn"],
  }),
  makeItem({
    id: "c",
    title: "Rust reader",
    priority: "P3",
    priority_label: "background",
    channel: "Dev > Rust",
    state: "seen",
    unread: true,
    summary: null,
    enrichment_failed: true,
  }),
];

const titles = () =>
  screen.getAllByRole("button", { name: /^(Django flaw|React 20 RC|Rust reader)$/ }).map((b) => b.textContent);

describe("the inbox", () => {
  it("shows a loading state then the items with their priority written out", async () => {
    mount(new FakeBackend(three()));
    expect(screen.getByText("Loading…")).toBeInTheDocument();
    expect(await screen.findByRole("button", { name: "Django flaw" })).toBeInTheDocument();
    const list = within(screen.getByRole("list", { name: "Items" }));
    expect(list.getByText("act today")).toBeInTheDocument();
    expect(list.getByText("react-blog, hn", { exact: false })).toBeInTheDocument();
    expect(list.getByText(/waiting for the model/)).toBeInTheDocument();
    expect(list.getByText(/the model could not read it/)).toBeInTheDocument();
    expect(list.getByRole("img", { name: "Starred" })).toBeInTheDocument();
    expect(screen.getByText("3 of 3")).toBeInTheDocument();
  });

  it("says so when there is nothing to look at", async () => {
    mount(new FakeBackend([]));
    expect(await screen.findByText(/Nothing to look at/)).toBeInTheDocument();
  });

  it("shows the error and tries again", async () => {
    const backend = new FakeBackend(three());
    backend.unreachable = true;
    const { user } = mount(backend);
    expect(await screen.findByRole("alert")).toHaveTextContent("Cannot reach Lookout");
    backend.unreachable = false;
    await user.click(screen.getByRole("button", { name: "Try again" }));
    expect(await screen.findByRole("button", { name: "Django flaw" })).toBeInTheDocument();
  });
});

describe("filters", () => {
  it("filters by priority, category, source, view, star and text, and keeps them in the URL", async () => {
    const hosts = [makeSource(), makeSource({ name: "hn" }), makeSource({ name: "react-blog" })];
    const { user } = mount(new FakeBackend(three(), hosts));
    await screen.findByRole("button", { name: "Django flaw" });

    await user.click(screen.getByRole("button", { name: "P0" }));
    await waitFor(() => {
      expect(titles()).toEqual(["Django flaw"]);
    });
    expect(window.location.search).toBe("?priority=P0");
    await user.click(screen.getByRole("button", { name: "P0" }));
    await waitFor(() => {
      expect(titles()).toHaveLength(3);
    });

    const tree = within(screen.getByRole("navigation", { name: "Categories" }));
    await user.click(tree.getByRole("button", { name: /^Rust/ }));
    await waitFor(() => {
      expect(titles()).toEqual(["Rust reader"]);
    });
    expect(window.location.search).toBe("?category=Dev+%3E+Rust");
    await user.click(tree.getByRole("button", { name: /^Dev/ }));
    await waitFor(() => {
      expect(titles()).toEqual(["Rust reader"]);
    });
    await user.click(tree.getByRole("button", { name: /^AI/ }));
    await waitFor(() => {
      expect(titles()).toEqual(["Django flaw", "React 20 RC"]);
    });
    expect(tree.getByRole("button", { name: /^AI/ })).toHaveAttribute("aria-current", "true");
    await user.click(tree.getByRole("button", { name: /^All/ }));
    await waitFor(() => {
      expect(titles()).toHaveLength(3);
    });
    expect(window.location.search).toBe("");

    await user.selectOptions(screen.getByLabelText("Source"), "hn");
    await waitFor(() => {
      expect(titles()).toEqual(["React 20 RC"]);
    });
    await user.selectOptions(screen.getByLabelText("Source"), "");

    await user.click(screen.getByRole("checkbox", { name: "Starred" }));
    await waitFor(() => {
      expect(titles()).toEqual(["Django flaw"]);
    });
    await user.click(screen.getByRole("checkbox", { name: "Starred" }));

    await user.type(screen.getByLabelText("Search"), "rust");
    await waitFor(() => {
      expect(titles()).toEqual(["Rust reader"]);
    });
    expect(window.location.search).toBe("?q=rust");
    await user.clear(screen.getByLabelText("Search"));

    await user.selectOptions(screen.getByLabelText("View"), "done");
    expect(await screen.findByText(/Nothing to look at/)).toBeInTheDocument();
    expect(window.location.search).toBe("?view=done");
  });

  it("starts from the filters in the URL and ignores nonsense in it", async () => {
    mount(
      new FakeBackend(three()),
      "/?priority=P1&priority=P9&view=nowhere&category=AI&source=hn&starred=true&q=react",
    );
    await waitFor(() => {
      expect(screen.queryByText("Loading…")).not.toBeInTheDocument();
    });
    expect(screen.getByRole("button", { name: "P1" })).toHaveAttribute("aria-pressed", "true");
    expect(screen.getByLabelText("View")).toHaveValue("inbox");
    expect(await screen.findByRole("button", { name: /^AI/ })).toHaveAttribute("aria-current", "true");
  });

  it("does not submit the form", async () => {
    const { user } = mount(new FakeBackend(three()));
    await screen.findByRole("button", { name: "Django flaw" });
    await user.type(screen.getByLabelText("Search"), "x");
    const form = screen.getByRole("search", { name: "Filter the inbox" });
    expect(fireEvent.submit(form)).toBe(false);
    expect(window.location.pathname).toBe("/");
  });
});

describe("views", () => {
  it("shows the state of items that are not in the inbox", async () => {
    const done = makeItem({ id: "d", title: "Handled", state: "done" });
    const { user } = mount(new FakeBackend([done, makeItem({ id: "n", title: "Fresh" })]));
    await screen.findByRole("button", { name: "Fresh" });
    await user.selectOptions(screen.getByLabelText("View"), "all");
    const row = (await screen.findByRole("button", { name: "Handled" })).closest("li");
    expect(row).toHaveTextContent("· done");
    expect(row).toHaveClass("done");
  });

  it("opens the shortcut help from its button", async () => {
    const { user } = mount(new FakeBackend(three()));
    await screen.findByRole("button", { name: "Django flaw" });
    await user.click(screen.getByRole("button", { name: "Shortcuts" }));
    expect(screen.getByRole("dialog", { name: "Keyboard shortcuts" })).toBeInTheDocument();
  });
});

describe("categories, tags and authors", () => {
  it("shows the category, the tags and the author of every item, and searches the author", async () => {
    const { user } = mount(new FakeBackend(three()));
    const row = (await screen.findByRole("button", { name: "Django flaw" })).closest("li") as HTMLElement;
    expect(within(row).getByText("AI")).toHaveClass("channel");
    expect(row).toHaveTextContent("#sql");
    expect(row).toHaveTextContent("by Jane Doe");
    await user.type(screen.getByLabelText("Search"), "jane");
    await waitFor(() => {
      expect(titles()).toEqual(["Django flaw"]);
    });
  });

  it("shows every declared category as a tree with counts that include what is under it", async () => {
    mount(new FakeBackend(three()));
    const tree = within(await screen.findByRole("navigation", { name: "Categories" }));
    const rows = tree.getAllByRole("listitem").map((li) => li.textContent);
    expect(rows).toEqual(["All3", "AI2", "Dev1", "Rust1", "Other0"]);
    expect(tree.getByRole("button", { name: /^All/ })).toHaveAttribute("aria-current", "true");
  });

  it("shows in the detail where the item is filed, who wrote it and its tags without repeats", async () => {
    const { user } = mount(new FakeBackend(three()));
    await user.click(await screen.findByRole("button", { name: "Django flaw" }));
    const detail = await screen.findByRole("complementary", { name: "Item detail" });
    expect(within(detail).getByText("AI")).toHaveClass("channel");
    expect(detail).toHaveTextContent("by Jane Doe");
    const tags = within(within(detail).getByRole("list", { name: "Tags" })).getAllByRole("listitem");
    expect(tags.map((t) => t.textContent)).toEqual(["django", "sql"]);
  });

  it("says when an item has not been read, has no author and no tags", async () => {
    const { user } = mount(
      new FakeBackend([makeItem({ id: "z", title: "Odd", tags: [], state: "seen", unread: true })]),
    );
    await user.click(await screen.findByRole("button", { name: "Odd" }));
    const detail = await screen.findByRole("complementary", { name: "Item detail" });
    expect(detail).toHaveTextContent("not read yet");
    expect(within(detail).queryByRole("list", { name: "Tags" })).not.toBeInTheDocument();
    expect(detail).not.toHaveTextContent("by ");
  });
});

describe("one item", () => {
  it("opens, marks the new item seen, and explains its rank", async () => {
    const backend = new FakeBackend(three());
    backend.detail = {
      explanation: {
        priority: "P0",
        priority_reason: "rule: critical advisory",
        model_score: 90,
        boost: -3,
        contributions: [
          { feature: "source:blog", points: -3 },
          { feature: "tag:x", points: 2 },
        ],
      },
    };
    const { user } = mount(backend);
    await user.click(await screen.findByRole("button", { name: "Django flaw" }));
    const detail = await screen.findByRole("complementary", { name: "Item detail" });
    expect(within(detail).getByText("Full text of Django flaw")).toBeInTheDocument();
    expect(within(detail).getByText("Action needed")).toBeInTheDocument();
    expect(within(detail).getByText("Touches your stack: django")).toBeInTheDocument();
    expect(within(detail).getByRole("link", { name: "Open the original" })).toHaveAttribute(
      "href",
      "https://example.test/a1",
    );
    expect(within(detail).getByText("rule: critical advisory")).toBeInTheDocument();
    expect(within(detail).getByText("Model score 90")).toBeInTheDocument();
    expect(within(detail).getByText(/moves it -3 inside P0/)).toBeInTheDocument();
    expect(within(detail).getByText("-3 source:blog")).toBeInTheDocument();
    expect(within(detail).getByText("+2 tag:x")).toBeInTheDocument();
    expect(window.location.search).toBe("?item=a");
    expect(
      backend.calls.some((c) => c.path === "/api/items/a/actions" && JSON.stringify(c.body).includes("open")),
    ).toBe(true);
    await user.click(within(detail).getByRole("button", { name: "Close" }));
    expect(screen.queryByRole("complementary")).not.toBeInTheDocument();
  });

  it("does not mark an item seen again", async () => {
    const backend = new FakeBackend(three());
    const { user } = mount(backend);
    await user.click(await screen.findByRole("button", { name: "Rust reader" }));
    await screen.findByRole("complementary");
    expect(backend.calls.filter((c) => c.path.endsWith("/actions"))).toHaveLength(0);
  });

  it("shows a detail for an unread item without score or summary, and a snooze date", async () => {
    const backend = new FakeBackend([
      makeItem({
        id: "z",
        title: "Odd",
        state: "seen",
        summary: null,
        snoozed_until: "2026-10-25T09:00:00Z",
        score: null,
      }),
    ]);
    backend.detail = {
      explanation: {
        priority: "P3",
        priority_reason: "no rule matched",
        model_score: null,
        boost: 4,
        contributions: [],
      },
    };
    const { user } = mount(backend);
    await user.click(await screen.findByRole("button", { name: "Odd" }));
    const detail = await screen.findByRole("complementary", { name: "Item detail" });
    expect(within(detail).queryByText(/Model score/)).not.toBeInTheDocument();
    expect(within(detail).getByText(/Snoozed until/)).toBeInTheDocument();
    expect(within(detail).getByText(/moves it \+4/)).toBeInTheDocument();
  });

  it("reports an item that cannot be loaded", async () => {
    const backend = new FakeBackend(three());
    const { user } = mount(backend, "/?item=ghost");
    expect(await screen.findByRole("alert")).toHaveTextContent("no item ghost");
    await user.click(screen.getByRole("button", { name: "Close" }));
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  });

  it("shows loading while the detail loads", async () => {
    mount(new FakeBackend(three()), "/?item=a");
    expect(await screen.findByLabelText("Item detail", {}, { timeout: 3000 })).toBeInTheDocument();
  });
});

describe("acting", () => {
  it("marks done and undoes it", async () => {
    const { user } = mount(new FakeBackend(three()));
    await user.click(await screen.findByRole("button", { name: "Django flaw" }));
    const detail = await screen.findByRole("complementary", { name: "Item detail" });
    await user.click(within(detail).getByRole("button", { name: /^Done/ }));
    expect(await screen.findByText("Marked done", { selector: ".toast" })).toBeInTheDocument();
    await waitFor(() => {
      expect(titles()).not.toContain("Django flaw");
    });
    // The finished item's detail goes with it, and the next item is the one in focus.
    expect(screen.queryByRole("complementary", { name: "Item detail" })).not.toBeInTheDocument();
    expect(screen.getByRole("listitem", { current: true })).toHaveTextContent("React 20 RC");
    await user.click(screen.getByRole("button", { name: "Undo" }));
    await waitFor(() => {
      expect(titles()).toContain("Django flaw");
    });
    expect(screen.queryByRole("button", { name: "Undo" })).not.toBeInTheDocument();
  });

  it("stars and unstars", async () => {
    const backend = new FakeBackend(three());
    const { user } = mount(backend);
    await user.click(await screen.findByRole("button", { name: "React 20 RC" }));
    const detail = await screen.findByRole("complementary", { name: "Item detail" });
    await user.click(within(detail).getByRole("button", { name: "Star" }));
    await user.click(await within(detail).findByRole("button", { name: "Unstar" }));
    await within(detail).findByRole("button", { name: "Star" });
  });

  it("reopens a finished item from the Done view", async () => {
    const backend = new FakeBackend([makeItem({ id: "d1", title: "Old news", state: "done" })]);
    const { user } = mount(backend, "/?view=done&item=d1");
    const detail = await screen.findByRole("complementary", { name: "Item detail" });
    expect(within(detail).queryByRole("button", { name: /^Done/ })).not.toBeInTheDocument();
    await user.click(await within(detail).findByRole("button", { name: "Reopen" }));
    expect(await screen.findByText("Reopened", { selector: ".toast" })).toBeInTheDocument();
  });

  it("snoozes from the detail and can cancel the menu", async () => {
    const backend = new FakeBackend(three());
    const { user } = mount(backend);
    await user.click(await screen.findByRole("button", { name: "React 20 RC" }));
    const detail = await screen.findByRole("complementary", { name: "Item detail" });
    await user.click(within(detail).getByRole("button", { name: "Snooze…" }));
    await user.click(screen.getByRole("button", { name: "Cancel" }));
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    await user.click(within(detail).getByRole("button", { name: "Snooze…" }));
    await user.click(screen.getByRole("button", { name: "4 hours" }));
    expect(await screen.findByText("Snoozed", { selector: ".toast" })).toBeInTheDocument();
    expect(backend.calls.filter((c) => c.path.endsWith("/actions")).at(-1)?.body).toMatchObject({
      action: "snooze",
      hours: 4,
    });
  });

  it("shows what the backend refused", async () => {
    const backend = new FakeBackend(three());
    const { user } = mount(backend);
    await user.click(await screen.findByRole("button", { name: "React 20 RC" }));
    const detail = await screen.findByRole("complementary", { name: "Item detail" });
    backend.failWith = { status: 409, detail: "already in the inbox" };
    await user.click(within(detail).getByRole("button", { name: /^Done/ }));
    expect(await screen.findByText("already in the inbox")).toBeInTheDocument();
  });

  it("shows when undo fails", async () => {
    const backend = new FakeBackend(three());
    const { user } = mount(backend);
    await user.click(await screen.findByRole("button", { name: "React 20 RC" }));
    const detail = await screen.findByRole("complementary", { name: "Item detail" });
    await user.click(within(detail).getByRole("button", { name: /^Done/ }));
    const undo = await screen.findByRole("button", { name: "Undo" });
    backend.failWith = { status: 404, detail: "no item b" };
    await user.click(undo);
    expect(await screen.findByText("no item b")).toBeInTheDocument();
  });

  it("lets the message go after a while", async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    const { user } = mount(new FakeBackend(three()));
    await user.click(await screen.findByRole("button", { name: "React 20 RC" }));
    const detail = await screen.findByRole("complementary", { name: "Item detail" });
    await user.click(within(detail).getByRole("button", { name: "Star" }));
    await screen.findByText("Starred", { selector: ".toast" });
    act(() => {
      vi.advanceTimersByTime(9000);
    });
    await waitFor(() => {
      expect(screen.queryByText("Starred", { selector: ".toast" })).not.toBeInTheDocument();
    });
  });

  it("marks the quiet items as seen", async () => {
    const { user } = mount(new FakeBackend(three()));
    await screen.findByRole("button", { name: "Django flaw" });
    await user.click(screen.getByRole("button", { name: "Mark P2 and P3 as seen" }));
    await waitFor(() => {
      expect(screen.getByRole("list", { name: "Items" })).toBeInTheDocument();
    });
  });
});

describe("keyboard", () => {
  it("moves, opens, acts, selects, undoes and shows help", async () => {
    const { user } = mount(new FakeBackend(three()));
    await screen.findByRole("button", { name: "Django flaw" });
    const current = () =>
      screen.getByRole("list", { name: "Items" }).querySelector("[aria-current]")?.textContent ?? "";

    expect(current()).toContain("Django flaw");
    await user.keyboard("j");
    expect(current()).toContain("React 20 RC");
    await user.keyboard("jj");
    expect(current()).toContain("Rust reader");
    await user.keyboard("kk");
    expect(current()).toContain("Django flaw");
    await user.keyboard("k");
    expect(current()).toContain("Django flaw");

    await user.keyboard("o");
    expect(await screen.findByRole("complementary")).toBeInTheDocument();
    await user.keyboard("j{Enter}");
    await waitFor(() => {
      expect(window.location.search).toBe("?item=b");
    });

    await user.keyboard("*");
    await screen.findByText("Starred", { selector: ".toast" });
    await user.keyboard("*");
    await screen.findByText("Unstarred", { selector: ".toast" });

    await user.keyboard("e");
    await screen.findByText("Marked done", { selector: ".toast" });
    await user.keyboard("u");
    await waitFor(() => {
      expect(titles()).toContain("React 20 RC");
    });

    await user.keyboard("+");
    await screen.findByText("More like this", { selector: ".toast" });
    await user.keyboard("-");
    await screen.findByText("Less like this", { selector: ".toast" });
    await user.keyboard("-");
    await screen.findByText("Rating cleared", { selector: ".toast" });
    await user.keyboard("=");
    await screen.findByText("More like this", { selector: ".toast" });

    await user.keyboard("s");
    await user.click(screen.getByRole("button", { name: "1 hour" }));
    await screen.findByText("Snoozed", { selector: ".toast" });

    await user.keyboard("?");
    expect(screen.getByRole("dialog", { name: "Keyboard shortcuts" })).toBeInTheDocument();
    await user.keyboard("{Escape}");
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    await user.keyboard("?");
    await user.click(within(screen.getByRole("dialog")).getByRole("button", { name: "Close" }));
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });

  it("does nothing on an empty inbox, and u without a message", async () => {
    mount(new FakeBackend([]));
    await screen.findByText(/Nothing to look at/);
    const { default: userEvent } = await import("@testing-library/user-event");
    const user = userEvent.setup();
    await user.keyboard("jkoes*x+-=u{Enter}");
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });

  it("ignores keys typed in a field and with a modifier", async () => {
    const { user } = mount(new FakeBackend(three()));
    await screen.findByRole("button", { name: "Django flaw" });
    await user.click(screen.getByLabelText("Search"));
    await user.keyboard("jd");
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    await user.click(document.body);
    await user.keyboard("{Control>}?{/Control}");
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    await user.keyboard("z");
  });
});

describe("bulk actions", () => {
  it("selects with the checkbox, acts on all, and clears", async () => {
    const backend = new FakeBackend(three());
    const { user } = mount(backend);
    await screen.findByRole("button", { name: "Django flaw" });
    await user.click(screen.getByLabelText("Select Django flaw"));
    await user.click(screen.getByLabelText("Select Django flaw"));
    expect(screen.queryByRole("group", { name: "Bulk actions" })).not.toBeInTheDocument();
    await user.click(screen.getByLabelText("Select Django flaw"));
    await user.click(screen.getByLabelText("Select React 20 RC"));
    const bar = screen.getByRole("group", { name: "Bulk actions" });
    expect(within(bar).getByText("2 selected")).toBeInTheDocument();
    await user.click(within(bar).getByRole("button", { name: "Clear" }));
    expect(screen.queryByRole("group", { name: "Bulk actions" })).not.toBeInTheDocument();

    await user.click(screen.getByLabelText("Select Django flaw"));
    await user.click(screen.getByLabelText("Select React 20 RC"));
    await user.click(screen.getByRole("button", { name: "Done" }));
    expect(await screen.findByText("Marked done: 2 items")).toBeInTheDocument();
    await waitFor(() => {
      expect(titles()).toEqual(["Rust reader"]);
    });
  });

  it("selects with x and the keys, and snoozes the selection", async () => {
    const { user } = mount(new FakeBackend(three()));
    await screen.findByRole("button", { name: "Django flaw" });
    await user.keyboard("x");
    await user.keyboard("jx");
    await user.click(document.body);
    expect(within(screen.getByRole("group", { name: "Bulk actions" })).getByText("2 selected")).toBeInTheDocument();
    await user.click(within(screen.getByRole("group", { name: "Bulk actions" })).getByRole("button", { name: "Done" }));
    expect(await screen.findByText("Marked done: 2 items")).toBeInTheDocument();

    await user.keyboard("x");
    await user.click(screen.getByRole("button", { name: "Snooze…" }));
    await user.click(screen.getByRole("button", { name: "Tomorrow" }));
    expect(await screen.findByText(/Snoozed/, { selector: ".toast" })).toBeInTheDocument();
  });

  it("snoozes several selected items at once, which leaves the focus alone", async () => {
    const { user } = mount(new FakeBackend(three()));
    await screen.findByRole("button", { name: "Django flaw" });
    await user.click(screen.getByLabelText("Select Django flaw"));
    await user.click(screen.getByLabelText("Select React 20 RC"));
    await user.click(screen.getByRole("button", { name: "Snooze…" }));
    await user.click(screen.getByRole("button", { name: "Tomorrow" }));
    expect(await screen.findByText("Snoozed: 2 items")).toBeInTheDocument();
  });

  it("drops items from the selection when they leave the list", async () => {
    const { user } = mount(new FakeBackend(three()));
    await screen.findByRole("button", { name: "Django flaw" });
    await user.click(screen.getByLabelText("Select Django flaw"));
    await user.click(screen.getByLabelText("Select React 20 RC"));
    await user.keyboard("e");
    await screen.findByText("Marked done: 2 items", { selector: ".toast" });
    expect(screen.queryByRole("group", { name: "Bulk actions" })).not.toBeInTheDocument();
  });
});

describe("running", () => {
  it("starts a run, shows progress, then refreshes the inbox", async () => {
    const backend = new FakeBackend([]);
    const { user } = mount(backend);
    await screen.findByText(/Nothing to look at/);
    backend.items = three();
    await user.click(screen.getByRole("button", { name: "Run now" }));
    expect(await screen.findByText("Running…")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Run now" })).toBeDisabled();
    expect(await screen.findByText("Last run: 3 new, 3 read", {}, { timeout: 4000 })).toBeInTheDocument();
    expect(await screen.findByRole("button", { name: "Django flaw" })).toBeInTheDocument();
  });

  it("says how many items are waiting for the model when the daily limit was reached, and why", async () => {
    const backend = new FakeBackend([]);
    backend.run = {
      ...backend.run,
      running: false,
      finished_at: "2026-10-24T09:00:00Z",
      enriched: 200,
      waiting: 240,
    };
    mount(backend);
    const status = await screen.findByRole("status");
    await waitFor(() => {
      expect(status).toHaveTextContent("Last run: 0 new, 200 read, 240 waiting for the model");
    });
    expect(status).toHaveAttribute("title", expect.stringContaining("daily model limit was reached"));
  });

  it("reports a failed run", async () => {
    const backend = new FakeBackend([]);
    backend.run = { ...backend.run, error: "OSError: disk full", running: false, finished_at: "2026-10-24T09:00:00Z" };
    mount(backend);
    expect(await screen.findByText("Last run failed: OSError: disk full")).toBeInTheDocument();
  });
});

describe("sources", () => {
  const sources = () => [
    makeSource(),
    makeSource({ name: "lobsters", enabled: false, last_run: null, last_error: "timeout", items_seen: 0 }),
  ];

  it("lists sources with their health and switches them", async () => {
    const backend = new FakeBackend(three(), sources());
    const { user } = mount(backend);
    await user.click(await screen.findByRole("link", { name: "Sources" }));
    expect(window.location.pathname).toBe("/sources");
    expect(await screen.findByRole("row", { name: /lobsters/ })).toHaveTextContent("never");
    expect(screen.getByRole("row", { name: /lobsters/ })).toHaveTextContent("timeout");
    expect(screen.getByRole("link", { name: "Sources" })).toHaveAttribute("aria-current", "page");
    await user.click(screen.getByRole("switch", { name: "Enable lobsters" }));
    await waitFor(() => {
      expect(screen.getByRole("switch", { name: "Enable lobsters" })).toBeChecked();
    });
    await user.click(screen.getByRole("link", { name: "Inbox" }));
    expect(await screen.findByRole("button", { name: "Django flaw" })).toBeInTheDocument();
  });

  it("shows what the backend refused", async () => {
    const backend = new FakeBackend([], sources());
    const { user } = mount(backend, "/sources");
    const toggle = await screen.findByRole("switch", { name: "Enable lobsters" });
    backend.failWith = { status: 409, detail: "lobsters is disabled in lookout.yaml; enable it there" };
    await user.click(toggle);
    expect(await screen.findByRole("alert")).toHaveTextContent("disabled in lookout.yaml");
  });

  it("says when no source is declared, and when they cannot be loaded", async () => {
    mount(new FakeBackend([], []), "/sources");
    expect(await screen.findByText(/No source yet/)).toBeInTheDocument();
  });

  it("can retry after an error", async () => {
    const backend = new FakeBackend([], sources());
    backend.unreachable = true;
    const { user } = mount(backend, "/sources");
    expect(await screen.findByRole("alert")).toHaveTextContent("Cannot reach Lookout");
    backend.unreachable = false;
    await user.click(screen.getByRole("button", { name: "Try again" }));
    expect(await screen.findByRole("switch", { name: "Enable blog" })).toBeInTheDocument();
  });

  it("shows loading first", () => {
    mount(new FakeBackend([], sources()), "/sources");
    expect(screen.getByText("Loading…")).toBeInTheDocument();
  });
});

describe("thumbs and done on every row", () => {
  const rowOf = async (title: string) => {
    const button = await screen.findByRole("button", { name: title });
    return button.closest("li") as HTMLElement;
  };

  it("rates up and down without moving the item, clears with the same thumb, and can undo", async () => {
    const backend = new FakeBackend(three());
    const { user } = mount(backend);
    const item = await rowOf("React 20 RC");
    const up = within(item).getByRole("button", { name: "More like this" });
    const down = within(item).getByRole("button", { name: "Less like this" });
    expect(up).toHaveAttribute("aria-pressed", "false");

    await user.click(up);
    expect(await screen.findByText("More like this", { selector: ".toast" })).toBeInTheDocument();
    await waitFor(() => {
      expect(within(item).getByRole("button", { name: "More like this" })).toHaveAttribute("aria-pressed", "true");
    });
    expect(titles()).toContain("React 20 RC");
    expect(backend.items.find((i) => i.id === "b")?.rating).toBe(1);

    await user.click(down);
    await screen.findByText("Less like this", { selector: ".toast" });
    expect(backend.items.find((i) => i.id === "b")?.rating).toBe(-1);

    await user.click(down);
    await screen.findByText("Rating cleared", { selector: ".toast" });
    expect(backend.items.find((i) => i.id === "b")?.rating).toBe(0);

    await user.click(up);
    await user.click(await screen.findByRole("button", { name: "Undo" }));
    await waitFor(() => {
      expect(backend.items.find((i) => i.id === "b")?.rating).toBe(0);
    });
  });

  it("clears an item from its row with Done, and the next item takes the focus", async () => {
    const backend = new FakeBackend(three());
    const { user } = mount(backend);
    const item = await rowOf("Django flaw");
    await user.click(within(item).getByRole("button", { name: "Done: Django flaw" }));
    await waitFor(() => {
      expect(titles()).toEqual(["React 20 RC", "Rust reader"]);
    });
    expect(screen.getByRole("listitem", { current: true })).toHaveTextContent("React 20 RC");
  });

  it("moves the focus back when the last item is cleared", async () => {
    const { user } = mount(new FakeBackend(three()));
    const last = await rowOf("Rust reader");
    await user.click(within(last).getByRole("button", { name: "Done: Rust reader" }));
    await waitFor(() => {
      expect(titles()).toEqual(["Django flaw", "React 20 RC"]);
    });
    expect(screen.getByRole("listitem", { current: true })).toHaveTextContent("React 20 RC");
  });

  it("rates from the detail too, showing the rating there", async () => {
    const backend = new FakeBackend(three());
    const { user } = mount(backend);
    await user.click(await screen.findByRole("button", { name: "Django flaw" }));
    const detail = await screen.findByRole("complementary", { name: "Item detail" });
    await user.click(within(detail).getByRole("button", { name: "Less like this" }));
    await waitFor(() => {
      expect(within(detail).getByRole("button", { name: "Less like this" })).toHaveAttribute("aria-pressed", "true");
    });
    expect(backend.items.find((i) => i.id === "a")?.rating).toBe(-1);
  });

  it("shows when a rating was refused", async () => {
    const backend = new FakeBackend(three());
    const { user } = mount(backend);
    const item = await rowOf("Django flaw");
    backend.failWith = { status: 404, detail: "no item a" };
    await user.click(within(item).getByRole("button", { name: "More like this" }));
    expect(await screen.findByText("no item a")).toBeInTheDocument();
  });

  it("shows when undoing a rating fails", async () => {
    const backend = new FakeBackend(three());
    const { user } = mount(backend);
    const item = await rowOf("Django flaw");
    await user.click(within(item).getByRole("button", { name: "More like this" }));
    const undo = await screen.findByRole("button", { name: "Undo" });
    backend.failWith = { status: 404, detail: "no item a" };
    await user.click(undo);
    expect(await screen.findByText("no item a")).toBeInTheDocument();
  });
});
