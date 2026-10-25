import { screen, waitFor, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { readLastVisit, rememberVisit } from "./lastVisit";
import { buildSearch, parseLocation } from "./router";
import { NO_FILTERS } from "./api/types";
import { FakeBackend, makeItem } from "./test/fakeBackend";
import { mount } from "./test/render";

beforeEach(() => {
  window.localStorage.clear();
});
afterEach(() => {
  vi.unstubAllGlobals();
});

/** Item `n` was published `n` days before the fake clock; the lower the number the newer. */
const aged = (n: number, overrides = {}) =>
  makeItem({
    id: `i${n}`,
    title: `Story ${n}`,
    published_at: new Date(Date.parse("2026-10-24T08:00:00Z") - n * 86_400_000).toISOString(),
    priority: n === 5 ? "P0" : "P2",
    channel: n % 2 ? "AI" : "Other",
    ...overrides,
  });

const stories = (count: number) => Array.from({ length: count }, (_, n) => aged(n));
const rows = () => within(screen.getByRole("list", { name: "Items" })).getAllByRole("listitem");

describe("orders and age", () => {
  it("orders by priority by default and strictly by date on Latest, kept in the URL", async () => {
    const { user } = mount(new FakeBackend([aged(0), aged(5), aged(1)]));
    expect(await screen.findByRole("button", { name: "Story 5" })).toBeInTheDocument();
    expect(rows()[0]).toHaveTextContent("Story 5");

    await user.click(screen.getByRole("button", { name: "Latest" }));
    expect(screen.getByRole("button", { name: "Latest" })).toHaveAttribute("aria-pressed", "true");
    await waitFor(() => {
      expect(rows()[0]).toHaveTextContent("Story 0");
    });
    expect(window.location.search).toContain("order=date");

    await user.click(screen.getByRole("button", { name: "Triage" }));
    await waitFor(() => {
      expect(rows()[0]).toHaveTextContent("Story 5");
    });
    expect(window.location.search).not.toContain("order");
  });

  it("filters by age and finds expired items in their own view", async () => {
    const backend = new FakeBackend([aged(1), aged(20), aged(40, { state: "expired" })]);
    const { user } = mount(backend);
    await screen.findByRole("button", { name: "Story 1" });
    await user.selectOptions(screen.getByLabelText("Age"), "older14");
    await waitFor(() => {
      expect(rows()).toHaveLength(1);
    });
    expect(rows()[0]).toHaveTextContent("Story 20");
    expect(window.location.search).toContain("age=older14");

    await user.selectOptions(screen.getByLabelText("Age"), "");
    await user.selectOptions(screen.getByLabelText("View"), "expired");
    expect(await screen.findByRole("button", { name: "Story 40" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Story 1" })).not.toBeInTheDocument();
  });
});

describe("pages", () => {
  it("loads fifty at a time and says the real total", async () => {
    const { user } = mount(new FakeBackend(stories(120)));
    await screen.findByRole("button", { name: "Story 0" });
    expect(rows()).toHaveLength(50);
    expect(screen.getByText("50 of 120")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Load more (50 of 120)" }));
    await waitFor(() => {
      expect(rows()).toHaveLength(100);
    });
    await user.click(screen.getByRole("button", { name: "Load more (100 of 120)" }));
    await waitFor(() => {
      expect(rows()).toHaveLength(120);
    });
    expect(screen.queryByRole("button", { name: /Load more/ })).not.toBeInTheDocument();
    expect(screen.getByText("120 of 120")).toBeInTheDocument();
  });
});

describe("the divider since the last visit", () => {
  it("is drawn on Latest above what was already there, with how many are new", async () => {
    rememberVisit(new Date("2026-10-22T12:00:00Z"));
    mount(new FakeBackend([aged(0), aged(1), aged(5)]), "/?order=date");
    await screen.findByRole("button", { name: "Story 0" });
    const divider = screen.getByText("2 new since your last visit");
    expect(divider.nextElementSibling).toHaveTextContent("Story 5");
  });

  it.each([
    ["on Triage", "/", new Date("2026-10-22T12:00:00Z")],
    ["on a first visit", "/?order=date", null],
    ["when nothing is new", "/?order=date", new Date("2027-01-01T00:00:00Z")],
    ["when everything is new", "/?order=date", new Date("2020-01-01T00:00:00Z")],
  ])("is not drawn %s", async (_name, url, visit) => {
    if (visit) rememberVisit(visit);
    mount(new FakeBackend([aged(0), aged(1), aged(5)]), url);
    await screen.findByRole("button", { name: "Story 0" });
    expect(screen.queryByText(/new since your last visit/)).not.toBeInTheDocument();
  });

  it("remembers the visit when the page is left", async () => {
    const { unmount } = mount(new FakeBackend([aged(0)]));
    await screen.findByRole("button", { name: "Story 0" });
    window.dispatchEvent(new Event("pagehide"));
    expect(readLastVisit()).not.toBeNull();
    window.localStorage.clear();
    unmount();
    expect(readLastVisit()).not.toBeNull();
  });

  it("copes with storage that cannot be used", () => {
    const blocked = {
      getItem: () => {
        throw new Error("blocked");
      },
      setItem: () => {
        throw new Error("blocked");
      },
    };
    vi.stubGlobal("localStorage", blocked);
    expect(readLastVisit()).toBeNull();
    expect(() => {
      rememberVisit(new Date());
    }).not.toThrow();
  });
});

describe("acting on everything a selection matches", () => {
  const backend = () => new FakeBackend([...stories(60), aged(70, { channel: "AI" })]);

  it("counts first, shows examples and changes nothing until asked", async () => {
    const fake = backend();
    const { user } = mount(fake);
    await screen.findByRole("button", { name: "Story 0" });
    await user.click(screen.getByRole("button", { name: "Act on all 61…" }));
    const dialog = await screen.findByRole("dialog", { name: "Act on everything shown" });
    expect(await within(dialog).findByText("61 items")).toBeInTheDocument();
    expect(within(dialog).getAllByRole("listitem")).toHaveLength(5);
    expect(fake.calls.filter((c) => c.path === "/api/items/sweep")).toHaveLength(1);
    expect(fake.items.every((i) => i.state === "new")).toBe(true);
    await user.click(within(dialog).getByRole("button", { name: "Cancel" }));
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });

  it("marks everything the filter matches, not only what is loaded, and can undo it", async () => {
    const fake = new FakeBackend([...stories(10), aged(70, { channel: "AI" })]);
    const { user } = mount(fake);
    await screen.findByRole("button", { name: "Story 0" });
    await user.selectOptions(screen.getByLabelText("Age"), "older30");
    await waitFor(() => {
      expect(screen.getByText("1 of 1")).toBeInTheDocument();
    });
    await user.click(screen.getByRole("button", { name: "Act on all 1…" }));
    const dialog = await screen.findByRole("dialog", { name: "Act on everything shown" });
    await user.click(await within(dialog).findByRole("button", { name: "Mark 1 done" }));
    expect(await screen.findByText("Marked done: 1 items")).toBeInTheDocument();
    expect(fake.items.find((i) => i.id === "i70")?.state).toBe("done");
    expect(fake.items.filter((i) => i.state === "done")).toHaveLength(1);

    await user.click(screen.getByRole("button", { name: "Undo" }));
    await waitFor(() => {
      expect(fake.items.find((i) => i.id === "i70")?.state).toBe("new");
    });
  });

  it("can rate everything the selection matches, up, down, or clear it, and says what that teaches", async () => {
    const fake = backend();
    const { user } = mount(fake);
    await screen.findByRole("button", { name: "Story 0" });
    await user.click(screen.getByRole("button", { name: "Act on all 61…" }));
    const dialog = await screen.findByRole("dialog", { name: "Act on everything shown" });
    await within(dialog).findByText("61 items");
    expect(within(dialog).getByText("thumb")).toBeInTheDocument();

    await user.click(within(dialog).getByRole("button", { name: "Less like this (61)" }));
    expect(await screen.findByText("Less like this: 61 items")).toBeInTheDocument();
    expect(fake.items.every((i) => i.rating === -1 && i.state === "new")).toBe(true); // rated, still in the inbox

    await user.click(screen.getByRole("button", { name: "Undo" }));
    await waitFor(() => {
      expect(fake.items.every((i) => i.rating === 0)).toBe(true);
    });

    await user.click(screen.getByRole("button", { name: "Act on all 61…" }));
    const again = await screen.findByRole("dialog", { name: "Act on everything shown" });
    await user.click(await within(again).findByRole("button", { name: "More like this (61)" }));
    await screen.findByText("More like this: 61 items");
    expect(fake.items.every((i) => i.rating === 1)).toBe(true);

    await user.click(screen.getByRole("button", { name: "Act on all 61…" }));
    const last = await screen.findByRole("dialog", { name: "Act on everything shown" });
    await user.click(await within(last).findByRole("button", { name: "Clear the rating (61)" }));
    await screen.findByText("Rating cleared: 61 items");
    expect(fake.items.every((i) => i.rating === 0)).toBe(true);
  });

  it("can dismiss or mark seen, and shows why it could not", async () => {
    const fake = backend();
    const { user } = mount(fake);
    await screen.findByRole("button", { name: "Story 0" });
    await user.click(screen.getByRole("button", { name: "Act on all 61…" }));
    let dialog = await screen.findByRole("dialog", { name: "Act on everything shown" });
    fake.failWith = { status: 422, detail: "6000 items match; narrow the filter to at most 5000" };
    await user.click(await within(dialog).findByRole("button", { name: "Mark 61 seen" }));
    expect(await within(dialog).findByRole("alert")).toHaveTextContent("narrow the filter");

    fake.failWith = null;
    await user.click(within(dialog).getByRole("button", { name: "Mark 61 seen" }));
    expect(await screen.findByText("Opened: 61 items")).toBeInTheDocument();
    expect(fake.items.every((i) => i.state === "seen")).toBe(true);
    dialog = screen.queryByRole("dialog") as HTMLElement;
    expect(dialog).toBeNull();
  });

  it("offers nothing to act on when nothing matches, and shows when undo fails", async () => {
    const fake = backend();
    const { user } = mount(fake);
    await screen.findByRole("button", { name: "Story 0" });
    await user.click(screen.getByRole("button", { name: "Act on all 61…" }));
    const dialog = await screen.findByRole("dialog", { name: "Act on everything shown" });
    await user.click(await within(dialog).findByRole("button", { name: "Mark 61 done" }));
    await screen.findByText("Marked done: 61 items");
    fake.failWith = { status: 404, detail: "no item i1" };
    await user.click(screen.getByRole("button", { name: "Undo" }));
    expect(await screen.findByText("no item i1")).toBeInTheDocument();
  });

  it("disables the choices when the count finds nothing any more", async () => {
    const fake = new FakeBackend([aged(1)]);
    const { user } = mount(fake);
    await screen.findByRole("button", { name: "Story 1" });
    const [only] = fake.items;
    if (only) only.state = "done"; // handled elsewhere since the list was loaded
    await user.click(screen.getByRole("button", { name: "Act on all 1…" }));
    const dialog = await screen.findByRole("dialog", { name: "Act on everything shown" });
    expect(await within(dialog).findByText("0 items")).toBeInTheDocument();
    expect(within(dialog).getByRole("button", { name: "Mark 0 done" })).toBeDisabled();
  });
});

describe("the address", () => {
  it("reads and writes the order and the age, and ignores nonsense", () => {
    const filters = { ...NO_FILTERS, order: "date" as const, age: "older30" as const, view: "expired" as const };
    expect(buildSearch(filters, null)).toBe("?view=expired&order=date&age=older30");
    expect(parseLocation("/", "?view=expired&order=date&age=older30").filters).toMatchObject(filters);
    expect(parseLocation("/", "?order=sideways&age=yesterday").filters).toMatchObject({ order: "priority", age: "" });
  });
});

describe("the counts beside the list", () => {
  const mixed = () => [
    aged(1, { channel: "AI" }),
    aged(2, { channel: "AI" }),
    aged(40, { channel: "AI" }),
    aged(3, { channel: "AI", state: "done" }),
    aged(4, { channel: "AI", state: "expired" }),
    aged(5, { channel: "Dev > Rust" }),
  ];
  const tree = () => within(screen.getByRole("navigation", { name: "Categories" }));
  const row = (name: RegExp) => tree().getByRole("button", { name }).textContent;

  it("count what the list shows, not everything ever filed", async () => {
    mount(new FakeBackend(mixed()));
    await screen.findByRole("button", { name: "Story 1" });
    // Five of the six items are in the AI or Dev branches, but one is done and one expired.
    expect(screen.getByText("4 of 4")).toBeInTheDocument();
    expect(row(/^All/)).toBe("All4");
    expect(row(/^AI/)).toBe("🤖AI3");
    expect(row(/^Dev/)).toBe("Dev1");
  });

  it("follow the age filter and the view, so a category number is what clicking it lists", async () => {
    const { user } = mount(new FakeBackend(mixed()));
    await screen.findByRole("button", { name: "Story 1" });
    await user.selectOptions(screen.getByLabelText("Age"), "older30");
    await waitFor(() => {
      expect(row(/^AI/)).toBe("🤖AI1");
    });
    expect(row(/^All/)).toBe("All1");
    await user.click(tree().getByRole("button", { name: /^AI/ }));
    await waitFor(() => {
      expect(screen.getByText("1 of 1")).toBeInTheDocument();
    });

    await user.selectOptions(screen.getByLabelText("Age"), "");
    await user.selectOptions(screen.getByLabelText("View"), "expired");
    await waitFor(() => {
      expect(row(/^AI/)).toBe("🤖AI1");
    });
    expect(row(/^All/)).toBe("All1");
    expect(screen.getByText("1 of 1")).toBeInTheDocument();
  });
});

describe("searching beyond the inbox", () => {
  const archive = () => [
    aged(1, { title: "Django release" }),
    aged(90, { title: "Django old news", state: "done" }),
    aged(200, { title: "Django ancient", state: "expired" }),
  ];

  it("says what a search looks at and widens it in one click, to every state and age", async () => {
    const { user } = mount(new FakeBackend(archive()));
    await screen.findByRole("button", { name: "Django release" });
    expect(screen.queryByText(/Searching only/)).not.toBeInTheDocument();

    await user.type(screen.getByLabelText("Search"), "django");
    const note = await screen.findByRole("note");
    expect(note).toHaveTextContent("Searching only Inbox");
    await waitFor(() => {
      expect(rows()).toHaveLength(1);
    });

    await user.selectOptions(screen.getByLabelText("Age"), "newer7");
    await user.click(within(note).getByRole("button", { name: "Search everything" }));
    await waitFor(() => {
      expect(rows()).toHaveLength(3);
    });
    expect(window.location.search).toContain("view=all");
    expect(window.location.search).not.toContain("age=");
    expect(screen.queryByText(/Searching only/)).not.toBeInTheDocument();
  });

  it("names the view that is being searched", async () => {
    mount(new FakeBackend(archive()), "/?view=done&q=django");
    expect(await screen.findByRole("note")).toHaveTextContent("Searching only Done");
  });
});
