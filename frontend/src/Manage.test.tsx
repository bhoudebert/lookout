import { screen, waitFor, within } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { FakeBackend, makeItem, makeSource } from "./test/fakeBackend";
import { mount } from "./test/render";

afterEach(() => {
  vi.unstubAllGlobals();
});

const world = () =>
  new FakeBackend(
    [],
    [
      makeSource({ name: "blog", channels: ["AI"], keywords: ["llm"] }),
      makeSource({ name: "gh", type: "github", settings: { repos: ["o/r"], watch: ["releases"] }, enabled: false }),
    ],
  );

const calls = (backend: FakeBackend, method: string, prefix: string) =>
  backend.calls.filter((c) => c.method === method && c.path.startsWith(prefix));

describe("sources", () => {
  it("lists each source with its type, channels (or model decides), health and a way to manage it", async () => {
    mount(world(), "/sources");
    const blog = await screen.findByRole("row", { name: /blog/ });
    expect(blog).toHaveTextContent("rss");
    expect(blog).toHaveTextContent("AI");
    expect(screen.getByRole("row", { name: /gh/ })).toHaveTextContent("model decides");
    expect(within(blog).getByRole("button", { name: "Edit blog" })).toBeInTheDocument();
    expect(within(blog).getByRole("button", { name: "Delete blog" })).toBeInTheDocument();
  });

  it("adds an RSS source with its channels and keywords", async () => {
    const backend = world();
    const { user } = mount(backend, "/sources");
    await user.click(await screen.findByRole("button", { name: "Add a source" }));
    const form = screen.getByRole("form", { name: "Add a source" });
    await user.type(within(form).getByLabelText("Name"), "rust-blog");
    await user.type(within(form).getByLabelText("Feed address"), " https://rust.test/feed.xml ");
    await user.click(within(form).getByRole("checkbox", { name: "Rust" }));
    await user.click(within(form).getByRole("checkbox", { name: "AI" }));
    await user.click(within(form).getByRole("checkbox", { name: "AI" }));
    await user.type(within(form).getByLabelText("Keywords"), "rust, , async");
    await user.click(within(form).getByRole("button", { name: "Add" }));

    expect(await screen.findByRole("row", { name: /rust-blog/ })).toHaveTextContent("Rust");
    expect(screen.queryByRole("form", { name: "Add a source" })).not.toBeInTheDocument();
    const [sent] = calls(backend, "POST", "/api/sources");
    expect(sent?.body).toEqual({
      name: "rust-blog",
      type: "rss",
      settings: { url: "https://rust.test/feed.xml" },
      channels: ["Rust"],
      keywords: ["rust", "async"],
      enabled: true,
    });
  });

  it("builds the form from the type: lists, numbers and switches", async () => {
    const backend = world();
    const { user } = mount(backend, "/sources");
    await user.click(await screen.findByRole("button", { name: "Add a source" }));
    const form = screen.getByRole("form", { name: "Add a source" });

    await user.selectOptions(within(form).getByLabelText("Type"), "GitHub repositories");
    expect(within(form).getByLabelText("Repositories")).toHaveValue("");
    expect(within(form).getByLabelText("Watch")).toHaveValue("releases\nadvisories");
    await user.type(within(form).getByLabelText("Name"), "repos");
    await user.type(within(form).getByLabelText("Repositories"), "o/a{Enter}  {Enter}o/b");
    await user.clear(within(form).getByLabelText("Watch"));
    await user.type(within(form).getByLabelText("Watch"), "dependabot");
    await user.click(within(form).getByRole("checkbox", { name: "Enabled" }));
    await user.click(within(form).getByRole("button", { name: "Add" }));
    await screen.findByRole("row", { name: /repos/ });
    expect(calls(backend, "POST", "/api/sources")[0]?.body).toMatchObject({
      type: "github",
      settings: { repos: ["o/a", "o/b"], watch: ["dependabot"] },
      enabled: false,
    });

    await user.click(screen.getByRole("button", { name: "Add a source" }));
    const second = screen.getByRole("form", { name: "Add a source" });
    await user.selectOptions(within(second).getByLabelText("Type"), "OSV vulnerabilities");
    expect(within(second).getByLabelText("Only the last (days)")).toHaveValue(30);
    expect(within(second).getByRole("checkbox", { name: "Flag CISA known-exploited" })).toBeChecked();
    await user.type(within(second).getByLabelText("Name"), "cves");
    await user.clear(within(second).getByLabelText("Only the last (days)"));
    await user.click(within(second).getByRole("checkbox", { name: "Flag CISA known-exploited" }));
    await user.click(within(second).getByRole("button", { name: "Add" }));
    await screen.findByRole("row", { name: /cves/ });
    expect(calls(backend, "POST", "/api/sources")[1]?.body).toMatchObject({
      type: "osv",
      settings: { kev: false },
    });
  });

  it("sends a number as a number", async () => {
    const backend = world();
    const { user } = mount(backend, "/sources");
    await user.click(await screen.findByRole("button", { name: "Add a source" }));
    const form = screen.getByRole("form", { name: "Add a source" });
    await user.selectOptions(within(form).getByLabelText("Type"), "OSV vulnerabilities");
    await user.type(within(form).getByLabelText("Name"), "cves");
    await user.clear(within(form).getByLabelText("Only the last (days)"));
    await user.type(within(form).getByLabelText("Only the last (days)"), "7");
    await user.click(within(form).getByRole("button", { name: "Add" }));
    await screen.findByRole("row", { name: /cves/ });
    expect(calls(backend, "POST", "/api/sources")[0]?.body).toMatchObject({ settings: { since_days: 7, kev: true } });
  });

  it("shows why a source was refused and keeps the form open with what was typed", async () => {
    const backend = world();
    const { user } = mount(backend, "/sources");
    await user.click(await screen.findByRole("button", { name: "Add a source" }));
    const form = screen.getByRole("form", { name: "Add a source" });
    await user.type(within(form).getByLabelText("Name"), "bad");
    backend.failWith = { status: 422, detail: "source 'bad' (rss): 'url' must start with http:// or https://" };
    await user.click(within(form).getByRole("button", { name: "Add" }));
    expect(await within(form).findByRole("alert")).toHaveTextContent("'url' must start with http");
    expect(within(form).getByLabelText("Name")).toHaveValue("bad");
    backend.failWith = null;
    await user.click(within(form).getByRole("button", { name: "Cancel" }));
    expect(screen.queryByRole("form", { name: /source|Edit/ })).not.toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Add a source" }));
    expect(within(screen.getByRole("form", { name: "Add a source" })).queryByRole("alert")).not.toBeInTheDocument();
  });

  it("edits a source: the name and type are fixed, everything else can change", async () => {
    const backend = world();
    const { user } = mount(backend, "/sources");
    await user.click(await screen.findByRole("button", { name: "Edit blog" }));
    const form = screen.getByRole("form", { name: "Edit blog" });
    expect(within(form).getByLabelText("Name")).toBeDisabled();
    expect(within(form).getByLabelText("Type")).toBeDisabled();
    expect(within(form).getByLabelText("Feed address")).toHaveValue("https://example.test/feed");
    expect(within(form).getByRole("checkbox", { name: "AI" })).toBeChecked();
    expect(within(form).getByLabelText("Keywords")).toHaveValue("llm");
    await user.clear(within(form).getByLabelText("Feed address"));
    await user.type(within(form).getByLabelText("Feed address"), "https://new.test/feed");
    await user.click(within(form).getByRole("checkbox", { name: "AI" }));
    await user.click(within(form).getByRole("button", { name: "Save" }));
    await waitFor(() => {
      expect(screen.queryByRole("form", { name: /source|Edit/ })).not.toBeInTheDocument();
    });
    expect(calls(backend, "PUT", "/api/sources/blog")[0]?.body).toEqual({
      type: "rss",
      settings: { url: "https://new.test/feed" },
      channels: [],
      keywords: ["llm"],
      enabled: true,
    });
    expect(screen.getByRole("row", { name: /blog/ })).toHaveTextContent("model decides");
  });

  it("shows why a change was refused", async () => {
    const backend = world();
    const { user } = mount(backend, "/sources");
    await user.click(await screen.findByRole("button", { name: "Edit blog" }));
    backend.failWith = { status: 422, detail: "source 'blog' feeds the channel 'X', which does not exist" };
    await user.click(screen.getByRole("button", { name: "Save" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("which does not exist");
  });

  it("edits a source of a type this version does not know, falling back to the first type", async () => {
    const backend = new FakeBackend([], [makeSource({ name: "old", type: "ftp", settings: {} })]);
    const { user } = mount(backend, "/sources");
    await user.click(await screen.findByRole("button", { name: "Edit old" }));
    const form = screen.getByRole("form", { name: "Edit old" });
    expect(within(form).getByLabelText("Feed address")).toHaveValue("");
  });

  it("switches an edit form to another source cleanly", async () => {
    const { user } = mount(world(), "/sources");
    await user.click(await screen.findByRole("button", { name: "Edit blog" }));
    await user.click(screen.getByRole("button", { name: "Edit gh" }));
    const form = screen.getByRole("form", { name: "Edit gh" });
    expect(within(form).getByLabelText("Repositories")).toHaveValue("o/r");
    expect(within(form).getByRole("checkbox", { name: "Enabled" })).not.toBeChecked();
  });

  it("deletes a source", async () => {
    const backend = world();
    const { user } = mount(backend, "/sources");
    await user.click(await screen.findByRole("button", { name: "Delete gh" }));
    await waitFor(() => {
      expect(screen.queryByRole("row", { name: /gh/ })).not.toBeInTheDocument();
    });
    expect(calls(backend, "DELETE", "/api/sources/gh")).toHaveLength(1);
  });

  it("shows when a delete is refused", async () => {
    const backend = world();
    const { user } = mount(backend, "/sources");
    const button = await screen.findByRole("button", { name: "Delete gh" });
    backend.failWith = { status: 404, detail: "no such source or channel: gh" };
    await user.click(button);
    expect(await screen.findByRole("alert")).toHaveTextContent("no such source");
  });

  it("invites you to add a first source", async () => {
    mount(new FakeBackend([], []), "/sources");
    expect(await screen.findByText(/No source yet/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Add a source" })).toBeInTheDocument();
  });

  it("edits a source with explicit switches and numbers", async () => {
    const backend = new FakeBackend(
      [],
      [makeSource({ name: "cves", type: "osv", settings: { kev: false, since_days: 7 } })],
    );
    const { user } = mount(backend, "/sources");
    await user.click(await screen.findByRole("button", { name: "Edit cves" }));
    const form = screen.getByRole("form", { name: "Edit cves" });
    expect(within(form).getByRole("checkbox", { name: "Flag CISA known-exploited" })).not.toBeChecked();
    expect(within(form).getByLabelText("Only the last (days)")).toHaveValue(7);
  });

  it.each(["/api/source-types", "/api/taxonomy"])(
    "shows an error when %s cannot be read, and recovers",
    async (path) => {
      const backend = world();
      backend.failOn = path;
      const { user } = mount(backend, "/sources");
      expect(await screen.findByRole("alert")).toHaveTextContent("broken");
      backend.failOn = null;
      await user.click(screen.getByRole("button", { name: "Try again" }));
      expect(await screen.findByRole("row", { name: /blog/ })).toBeInTheDocument();
    },
  );

  it("says when the server knows no type of source", async () => {
    const backend = world();
    backend.sourceTypes = [];
    mount(backend, "/sources");
    expect(await screen.findByRole("alert")).toHaveTextContent("knows no type of source");
  });
});

describe("categories", () => {
  const calls = (backend: FakeBackend, method: string, prefix: string) =>
    backend.calls.filter((c) => c.method === method && c.path.startsWith(prefix));

  it("lists each category with its description, its item count and who feeds it", async () => {
    mount(world(), "/categories");
    const panel = await screen.findByRole("region", { name: "Categories" });
    const ai = within(panel).getByText("AI").closest("li") as HTMLElement;
    expect(ai).toHaveTextContent("2 items");
    expect(ai).toHaveTextContent("Models");
    expect(ai).toHaveTextContent("fed by blog");
    const rust = within(panel).getByText("Rust").closest("li") as HTMLElement;
    expect(rust).toHaveTextContent("any source may file items here");
    expect(rust).toHaveTextContent("no description");
  });

  it("copes with a category the server sends without its sources", async () => {
    const backend = world();
    backend.taxonomy.channels = [{ name: "Web", description: "", items: 0 }];
    mount(backend, "/categories");
    const web = (await screen.findByText("Web")).closest("li") as HTMLElement;
    expect(web).toHaveTextContent("any source may file items here");
  });

  it("is reachable from the navigation", async () => {
    const { user } = mount(world(), "/");
    await user.click(await screen.findByRole("link", { name: "Categories" }));
    expect(await screen.findByRole("region", { name: "Categories" })).toBeInTheDocument();
    expect(window.location.pathname).toBe("/categories");
    expect(screen.getByRole("link", { name: "Categories" })).toHaveAttribute("aria-current", "page");
  });

  it("suggests starting categories and adds one with a click", async () => {
    const backend = world();
    const { user } = mount(backend, "/categories");
    const suggestions = await screen.findByRole("group", { name: "Suggested categories" });
    expect(within(suggestions).queryByRole("button", { name: "+ AI" })).not.toBeInTheDocument();
    await user.click(within(suggestions).getByRole("button", { name: "+ Security" }));
    expect(await screen.findByRole("button", { name: "Edit Security" })).toBeInTheDocument();
    expect(calls(backend, "POST", "/api/channels")[0]?.body).toMatchObject({ name: "Security" });
    await waitFor(() => {
      expect(
        within(screen.getByRole("group", { name: "Suggested categories" })).queryByRole("button", {
          name: "+ Security",
        }),
      ).not.toBeInTheDocument();
    });
  });

  it("stops suggesting when every suggestion exists", async () => {
    const backend = world();
    backend.taxonomy.channels = ["AI", "Rust", "Security", "Web", "Languages", "Cloud", "Data", "Other"].map(
      (name) => ({
        name,
        description: "",
        items: 0,
        sources: [],
      }),
    );
    mount(backend, "/categories");
    await screen.findByRole("region", { name: "Categories" });
    expect(screen.queryByRole("group", { name: "Suggested categories" })).not.toBeInTheDocument();
  });

  it("adds a category of your own and empties the form", async () => {
    const backend = world();
    const { user } = mount(backend, "/categories");
    const form = await screen.findByRole("form", { name: "Add a category" });
    await user.type(within(form).getByLabelText("New category"), "Gardening");
    await user.type(within(form).getByLabelText("Description"), "Plants");
    await user.click(within(form).getByRole("button", { name: "Add category" }));
    expect(await screen.findByRole("button", { name: "Edit Gardening" })).toBeInTheDocument();
    expect(within(form).getByLabelText("New category")).toHaveValue("");
    expect(calls(backend, "POST", "/api/channels")[0]?.body).toEqual({ name: "Gardening", description: "Plants" });
    await user.click(screen.getByRole("link", { name: "Sources" }));
    await user.click(await screen.findByRole("button", { name: "Add a source" }));
    expect(
      within(screen.getByRole("form", { name: "Add a source" })).getByRole("checkbox", { name: "Gardening" }),
    ).toBeInTheDocument();
  });

  it("changes a description, or cancels", async () => {
    const backend = world();
    const { user } = mount(backend, "/categories");
    await user.click(await screen.findByRole("button", { name: "Edit Rust" }));
    await user.click(screen.getByRole("button", { name: "Cancel" }));
    expect(screen.queryByLabelText("Description of Rust")).not.toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Edit AI" }));
    const input = screen.getByLabelText("Description of AI");
    expect(input).toHaveValue("Models");
    await user.clear(input);
    await user.type(input, "Models and agents");
    await user.click(screen.getByRole("button", { name: "Save" }));
    expect(await screen.findByText("Models and agents")).toBeInTheDocument();
    expect(calls(backend, "PATCH", "/api/channels/AI")[0]?.body).toEqual({ description: "Models and agents" });
  });

  it("deletes a category", async () => {
    const { user } = mount(world(), "/categories");
    await user.click(await screen.findByRole("button", { name: "Delete Rust" }));
    await waitFor(() => {
      expect(screen.queryByRole("button", { name: "Edit Rust" })).not.toBeInTheDocument();
    });
  });

  it("shows only the latest refusal", async () => {
    const backend = world();
    const { user } = mount(backend, "/categories");
    const form = await screen.findByRole("form", { name: "Add a category" });
    backend.failWith = { status: 409, detail: "the channel 'AI' is fed by blog: change those sources first" };
    await user.click(screen.getByRole("button", { name: "Delete AI" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("fed by blog");
    backend.failWith = { status: 409, detail: "a channel named 'rust' already exists" };
    await user.type(within(form).getByLabelText("New category"), "rust");
    await user.click(within(form).getByRole("button", { name: "Add category" }));
    await waitFor(() => {
      expect(screen.getByRole("alert")).toHaveTextContent("already exists");
    });
    expect(within(form).getByLabelText("New category")).toHaveValue("rust");
  });

  it("files existing items again and says what will happen", async () => {
    const backend = world();
    const { user } = mount(backend, "/categories");
    await user.click(await screen.findByRole("button", { name: "File existing items again" }));
    expect(await screen.findByText(/Filed 2 by rule\. 5 will be read again by the model/)).toBeInTheDocument();
    expect(calls(backend, "POST", "/api/refile")).toHaveLength(1);
  });

  it("shows when filing again fails", async () => {
    const backend = world();
    const { user } = mount(backend, "/categories");
    const button = await screen.findByRole("button", { name: "File existing items again" });
    backend.failWith = { status: 500, detail: "disk full" };
    await user.click(button);
    expect(await screen.findByRole("alert")).toHaveTextContent("disk full");
  });

  it("manages the kinds, and keeps other", async () => {
    const backend = world();
    const { user } = mount(backend, "/categories");
    const kinds = await screen.findByRole("region", { name: "Kinds" });
    expect(within(kinds).getByText("other")).toBeInTheDocument();
    expect(within(kinds).queryByRole("button", { name: "Delete kind other" })).not.toBeInTheDocument();
    const form = screen.getByRole("form", { name: "Add a kind" });
    await user.type(within(form).getByLabelText("New kind"), "Weekly Digest");
    await user.click(within(form).getByRole("button", { name: "Add kind" }));
    expect(await within(kinds).findByText("weekly digest")).toBeInTheDocument();
    expect(within(form).getByLabelText("New kind")).toHaveValue("");
    await user.click(within(kinds).getByRole("button", { name: "Delete kind weekly digest" }));
    await waitFor(() => {
      expect(within(kinds).queryByText("weekly digest")).not.toBeInTheDocument();
    });
  });

  it("says when categories cannot be read, and recovers", async () => {
    const backend = world();
    backend.failOn = "/api/taxonomy";
    const { user } = mount(backend, "/categories");
    expect(await screen.findByRole("alert")).toHaveTextContent("broken");
    backend.failOn = null;
    await user.click(screen.getByRole("button", { name: "Try again" }));
    expect(await screen.findByRole("region", { name: "Categories" })).toBeInTheDocument();
  });

  it("shows loading first", () => {
    mount(world(), "/categories");
    expect(screen.getByText("Loading…")).toBeInTheDocument();
  });
});

describe("the inbox nudge", () => {
  it("says so while everything is in Other, and points to the categories", async () => {
    mount(
      new FakeBackend([
        makeItem({ id: "a", title: "One", channel: "Other" }),
        makeItem({ id: "b", title: "Two", channel: "Other" }),
      ]),
    );
    const note = await screen.findByRole("note");
    expect(note).toHaveTextContent("Everything here is in Other");
    expect(within(note).getByRole("link", { name: "Define categories" })).toHaveAttribute("href", "/categories");
  });

  it("is quiet once an item is filed, and on an empty inbox", async () => {
    const first = mount(new FakeBackend([makeItem({ id: "a", title: "One", channel: "AI" })]));
    await screen.findByRole("button", { name: "One" });
    expect(screen.queryByRole("note")).not.toBeInTheDocument();
    first.unmount();
    mount(new FakeBackend([]));
    await screen.findByText(/Nothing to look at/);
    expect(screen.queryByRole("note")).not.toBeInTheDocument();
  });
});
