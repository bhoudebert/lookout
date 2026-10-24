import { screen, waitFor, within } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { FakeBackend, makeItem, makeSource } from "./test/fakeBackend";
import { mount } from "./test/render";

afterEach(() => {
  vi.unstubAllGlobals();
});

const world = () =>
  new FakeBackend(
    [
      makeItem({ id: "x1", channel: "AI" }),
      makeItem({ id: "x2", channel: "AI" }),
      makeItem({ id: "x3", channel: "Dev > Rust" }),
    ],
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

  it("suggests sources, and adds one with the category it files in", async () => {
    const backend = world();
    const { user } = mount(backend, "/sources");
    const group = await screen.findByRole("group", { name: "Suggested sources" });
    expect(within(group).queryByRole("button", { name: "+ Lobsters: hottest" })).toBeInTheDocument();
    await user.click(within(group).getByRole("button", { name: "+ Inside Java" }));
    expect(await screen.findByRole("row", { name: /Inside Java/ })).toHaveTextContent("Dev > Java");
    expect(calls(backend, "POST", "/api/channels")[0]?.body).toEqual({
      name: "Dev > Java",
      description: "Java, the JVM and its ecosystem",
    });
    expect(calls(backend, "POST", "/api/sources")[0]?.body).toMatchObject({
      name: "Inside Java",
      type: "rss",
      channels: ["Dev > Java"],
      settings: { url: "https://inside.java/feed.xml" },
    });
    expect(within(group).queryByRole("button", { name: "+ Inside Java" })).not.toBeInTheDocument();
  });

  it("adds a suggested source into a category that exists without creating it again", async () => {
    const backend = world();
    const { user } = mount(backend, "/sources");
    await user.click(await screen.findByRole("button", { name: "+ Hugging Face Blog" }));
    expect(await screen.findByRole("row", { name: /Hugging Face Blog/ })).toHaveTextContent("AI");
    expect(calls(backend, "POST", "/api/channels")).toHaveLength(0);
  });

  it("adds a suggested source that lets the model choose the category", async () => {
    const backend = world();
    const { user } = mount(backend, "/sources");
    await user.click(await screen.findByRole("button", { name: "+ Hacker News" }));
    expect(await screen.findByRole("row", { name: /Hacker News/ })).toHaveTextContent("model decides");
    expect(calls(backend, "POST", "/api/sources")[0]?.body).toMatchObject({
      type: "hackernews",
      channels: [],
      settings: { feed: "front_page", min_points: 100 },
    });
  });

  it("does not suggest a source already there under another name", async () => {
    const backend = new FakeBackend(
      [],
      [makeSource({ name: "my rust", settings: { url: "https://blog.rust-lang.org/feed.xml" } })],
    );
    mount(backend, "/sources");
    await screen.findByRole("row", { name: /my rust/ });
    expect(screen.queryByRole("button", { name: "+ Rust Blog" })).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "+ Inside Rust" })).toBeInTheDocument();
  });

  it("shows why a suggested source was refused", async () => {
    const backend = world();
    const { user } = mount(backend, "/sources");
    await screen.findByRole("group", { name: "Suggested sources" });
    backend.failWith = { status: 409, detail: "a source named 'Lobsters: hottest' already exists" };
    await user.click(screen.getByRole("button", { name: "+ Lobsters: hottest" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("a source named 'Lobsters: hottest' already exists");
    expect(screen.getByRole("button", { name: "+ Lobsters: hottest" })).toBeEnabled();
  });

  it("groups the suggestions by theme and hides a theme once all of it is there", async () => {
    const { PRESETS } = await import("./presets");
    const backend = new FakeBackend(
      [],
      PRESETS.filter((p) => p.group === "rust").map((p) => makeSource({ name: p.name, settings: p.settings })),
    );
    mount(backend, "/sources");
    const group = await screen.findByRole("group", { name: "Suggested sources" });
    expect(within(group).queryByText("Rust")).not.toBeInTheDocument();
    expect(within(group).getByText("Service status")).toBeInTheDocument();
    expect(within(group).getByText("Reddit communities")).toBeInTheDocument();
    expect(within(group).getByText(/one request a minute/)).toBeInTheDocument();
  });

  it("adds a Reddit suggestion with all its communities and the category it files in", async () => {
    const backend = world();
    const { user } = mount(backend, "/sources");
    await user.click(await screen.findByRole("button", { name: "+ Reddit: France" }));
    expect(await screen.findByRole("row", { name: /Reddit: France/ })).toHaveTextContent("News > France");
    expect(calls(backend, "POST", "/api/channels")[0]?.body).toMatchObject({ name: "News > France" });
    expect(calls(backend, "POST", "/api/sources")[0]?.body).toMatchObject({
      type: "reddit",
      settings: { subreddits: ["france", "programmation"], sort: "hot" },
      channels: ["News > France"],
    });
  });

  it("adds a YouTube channel by its handle", async () => {
    const backend = world();
    const { user } = mount(backend, "/sources");
    await user.click(await screen.findByRole("button", { name: "+ YouTube: Fireship" }));
    expect(await screen.findByRole("row", { name: /YouTube: Fireship/ })).toBeInTheDocument();
    expect(calls(backend, "POST", "/api/sources")[0]?.body).toMatchObject({
      type: "youtube",
      settings: { channel: "@fireship" },
    });
  });

  it("stops suggesting once every suggestion is there", async () => {
    const { PRESETS } = await import("./presets");
    const backend = new FakeBackend(
      [],
      PRESETS.map((p) => makeSource({ name: p.name, settings: p.settings })),
    );
    mount(backend, "/sources");
    await screen.findByRole("row", { name: /Lobsters: hottest/ });
    expect(screen.queryByRole("group", { name: "Suggested sources" })).not.toBeInTheDocument();
  });

  it("says in words where the items will go, for what is ticked", async () => {
    const { user } = mount(world(), "/sources");
    await user.click(await screen.findByRole("button", { name: "Add a source" }));
    const form = screen.getByRole("form", { name: "Add a source" });
    expect(within(form).getByText(/None ticked: the model chooses a category for each item/)).toBeInTheDocument();
    await user.click(within(form).getByRole("checkbox", { name: "AI" }));
    expect(
      within(form).getByText("Every item goes straight to AI. The model is not asked to choose."),
    ).toBeInTheDocument();
    await user.click(within(form).getByRole("checkbox", { name: "Dev > Rust" }));
    expect(within(form).getByText("The model chooses for each item, among these 2.")).toBeInTheDocument();
  });

  it("creates a category from the form, ticks it and files the source in it", async () => {
    const backend = world();
    const { user } = mount(backend, "/sources");
    await user.click(await screen.findByRole("button", { name: "Add a source" }));
    const form = screen.getByRole("form", { name: "Add a source" });
    await user.type(within(form).getByLabelText("Name"), "moto");
    await user.type(within(form).getByLabelText("Feed address"), "https://moto.test/feed");
    await user.type(within(form).getByLabelText("New category"), "Hobbies > Motorcycles");
    await user.type(within(form).getByLabelText("Description"), "riding and my CB750");
    await user.click(within(form).getByRole("button", { name: "Create and tick" }));
    expect(await within(form).findByRole("checkbox", { name: "Hobbies > Motorcycles" })).toBeChecked();
    expect(within(form).getByLabelText("New category")).toHaveValue("");
    expect(
      within(form).getByText("Every item goes straight to Hobbies > Motorcycles. The model is not asked to choose."),
    ).toBeInTheDocument();
    await user.click(within(form).getByRole("button", { name: "Add" }));
    expect(await screen.findByRole("row", { name: /moto/ })).toHaveTextContent("Hobbies > Motorcycles");
    expect(calls(backend, "POST", "/api/channels")[0]?.body).toEqual({
      name: "Hobbies > Motorcycles",
      description: "riding and my CB750",
    });
    expect(calls(backend, "POST", "/api/sources")[0]?.body).toMatchObject({ channels: ["Hobbies > Motorcycles"] });
  });

  it("shows why a category could not be created from the form and keeps what was typed", async () => {
    const backend = world();
    const { user } = mount(backend, "/sources");
    await user.click(await screen.findByRole("button", { name: "Add a source" }));
    const form = screen.getByRole("form", { name: "Add a source" });
    await user.type(within(form).getByLabelText("New category"), "AI");
    backend.failWith = { status: 409, detail: "a category named 'AI' already exists" };
    await user.click(within(form).getByRole("button", { name: "Create and tick" }));
    expect(await within(form).findByRole("alert")).toHaveTextContent("a category named 'AI' already exists");
    expect(within(form).getByLabelText("New category")).toHaveValue("AI");
  });

  it("adds an RSS source with its channels and keywords", async () => {
    const backend = world();
    const { user } = mount(backend, "/sources");
    await user.click(await screen.findByRole("button", { name: "Add a source" }));
    const form = screen.getByRole("form", { name: "Add a source" });
    await user.type(within(form).getByLabelText("Name"), "rust-blog");
    await user.type(within(form).getByLabelText("Feed address"), " https://rust.test/feed.xml ");
    await user.click(within(form).getByRole("checkbox", { name: "Dev > Rust" }));
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
      channels: ["Dev > Rust"],
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

  it("lists the categories as a tree with descriptions, counts and who feeds each", async () => {
    mount(world(), "/categories");
    const panel = await screen.findByRole("region", { name: "Categories" });
    const ai = within(panel).getByRole("button", { name: "Edit AI" }).closest("li") as HTMLElement;
    expect(ai).toHaveTextContent("2 in the inbox");
    expect(ai).toHaveTextContent("Models");
    expect(ai).toHaveTextContent("fed by blog");
    const dev = within(panel).getByRole("button", { name: "Edit Dev" }).closest("li") as HTMLElement;
    expect(dev).toHaveTextContent("1 in the inbox");
    expect(dev).toHaveTextContent("any source may file items here");
    const rust = within(panel).getByRole("button", { name: "Edit Dev > Rust" }).closest("li") as HTMLElement;
    expect(rust.style.paddingLeft).toBe("1.5rem");
    expect(within(rust).getByText("Rust")).toHaveAttribute("title", "Dev > Rust");
  });

  it("copes with a category the server sends without its sources", async () => {
    const backend = world();
    backend.taxonomy.channels = [{ name: "Web", description: "", items: 0 }];
    mount(backend, "/categories");
    const web = (await screen.findByRole("button", { name: "Edit Web" })).closest("li") as HTMLElement;
    expect(web).toHaveTextContent("any source may file items here");
  });

  it("is reachable from the navigation", async () => {
    const { user } = mount(world(), "/");
    await user.click(
      within(await screen.findByRole("navigation", { name: "Main" })).getByRole("link", { name: "Categories" }),
    );
    expect(await screen.findByRole("region", { name: "Categories" })).toBeInTheDocument();
    expect(window.location.pathname).toBe("/categories");
  });

  it("suggests starting categories, including nested ones, and adds one with a click", async () => {
    const backend = world();
    const { user } = mount(backend, "/categories");
    const suggestions = await screen.findByRole("group", { name: "Suggested categories" });
    expect(within(suggestions).queryByRole("button", { name: "+ AI" })).not.toBeInTheDocument();
    expect(within(suggestions).queryByRole("button", { name: "+ Dev > Rust" })).not.toBeInTheDocument();
    await user.click(within(suggestions).getByRole("button", { name: "+ Dev > Python" }));
    expect(await screen.findByRole("button", { name: "Edit Dev > Python" })).toBeInTheDocument();
    expect(calls(backend, "POST", "/api/channels")[0]?.body).toMatchObject({ name: "Dev > Python" });
  });

  it("stops suggesting when every suggestion exists", async () => {
    const backend = world();
    backend.taxonomy.channels = [
      "AI",
      "Dev",
      "Dev > Rust",
      "Dev > Python",
      "Dev > Web",
      "Security",
      "Cloud",
      "Data",
      "Other",
    ].map((name) => ({ name, description: "", items: 0, sources: [] }));
    mount(backend, "/categories");
    await screen.findByRole("region", { name: "Categories" });
    expect(screen.queryByRole("group", { name: "Suggested categories" })).not.toBeInTheDocument();
  });

  it("adds a category inside another one, and empties the form", async () => {
    const backend = world();
    const { user } = mount(backend, "/categories");
    const form = await screen.findByRole("form", { name: "Add a category" });
    const inside = within(form).getByLabelText("Inside");
    expect(
      within(inside)
        .getAllByRole("option")
        .map((o) => o.textContent),
    ).toEqual(["(top level)", "AI", "Dev", "Dev > Rust"]);
    await user.selectOptions(inside, "Dev");
    await user.type(within(form).getByLabelText("New category"), "Gardening");
    await user.type(within(form).getByLabelText("Description"), "Plants");
    await user.click(within(form).getByRole("button", { name: "Add category" }));
    expect(await screen.findByRole("button", { name: "Edit Dev > Gardening" })).toBeInTheDocument();
    expect(within(form).getByLabelText("New category")).toHaveValue("");
    expect(calls(backend, "POST", "/api/channels")[0]?.body).toEqual({
      name: "Dev > Gardening",
      description: "Plants",
    });
  });

  it("adds a top-level category when nothing is chosen to put it in", async () => {
    const backend = world();
    const { user } = mount(backend, "/categories");
    const form = await screen.findByRole("form", { name: "Add a category" });
    await user.type(within(form).getByLabelText("New category"), "Cloud");
    await user.click(within(form).getByRole("button", { name: "Add category" }));
    expect(await screen.findByRole("button", { name: "Edit Cloud" })).toBeInTheDocument();
    expect(calls(backend, "POST", "/api/channels")[0]?.body).toEqual({ name: "Cloud", description: "" });
  });

  it("changes a description, or cancels", async () => {
    const backend = world();
    const { user } = mount(backend, "/categories");
    await user.click(await screen.findByRole("button", { name: "Edit Dev > Rust" }));
    await user.click(screen.getByRole("button", { name: "Cancel" }));
    expect(screen.queryByLabelText("Description of Dev > Rust")).not.toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Edit AI" }));
    const input = screen.getByLabelText("Description of AI");
    expect(input).toHaveValue("Models");
    await user.clear(input);
    await user.type(input, "Models and agents");
    await user.click(screen.getByRole("button", { name: "Save" }));
    expect(await screen.findByText("Models and agents")).toBeInTheDocument();
    expect(calls(backend, "PATCH", "/api/channels/AI")[0]?.body).toEqual({ description: "Models and agents" });
  });

  it("shows why a move was refused and keeps the tree as the server has it", async () => {
    const backend = world();
    const { user } = mount(backend, "/categories");
    await user.click(await screen.findByRole("button", { name: "Move AI" }));
    backend.failWith = { status: 404, detail: "no such source or channel: Dev" };
    await user.click(within(screen.getByRole("group", { name: "Move AI" })).getByRole("button", { name: "Move here" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("no such source or channel: Dev");
    expect(screen.getByRole("button", { name: "Edit AI" })).toBeInTheDocument();
  });

  it("offers no move when there is nowhere to go", async () => {
    const backend = world();
    backend.taxonomy.channels = [{ name: "AI", description: "", items: 0, sources: [] }];
    mount(backend, "/categories");
    expect(await screen.findByRole("button", { name: "Edit AI" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Move AI" })).not.toBeInTheDocument();
  });

  it("moves a category inside another, or back to the top level, or cancels", async () => {
    const backend = world();
    const { user } = mount(backend, "/categories");
    expect(await screen.findByRole("button", { name: "Edit Other" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Move Other" })).not.toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Move AI" }));
    await user.click(within(screen.getByRole("group", { name: "Move AI" })).getByRole("button", { name: "Cancel" }));
    expect(screen.queryByRole("group", { name: "Move AI" })).not.toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Move AI" }));
    const group = screen.getByRole("group", { name: "Move AI" });
    expect(
      within(group)
        .getAllByRole("option")
        .map((o) => o.textContent),
    ).toEqual(["Dev", "Dev > Rust"]);
    await user.selectOptions(within(group).getByLabelText("Move AI inside"), "Dev");
    await user.click(within(group).getByRole("button", { name: "Move here" }));
    expect(await screen.findByRole("button", { name: "Edit Dev > AI" })).toBeInTheDocument();
    expect(calls(backend, "POST", "/api/channels/AI/move")[0]?.body).toEqual({ parent: "Dev" });

    await user.click(screen.getByRole("button", { name: "Move Dev > Rust" }));
    expect(
      within(screen.getByRole("group", { name: "Move Dev > Rust" }))
        .getAllByRole("option")
        .map((o) => o.textContent),
    ).toEqual(["(top level)", "Dev > AI"]);
    await user.click(
      within(screen.getByRole("group", { name: "Move Dev > Rust" })).getByRole("button", { name: "Move here" }),
    );
    expect(await screen.findByRole("button", { name: "Edit Rust" })).toBeInTheDocument();
    expect(calls(backend, "POST", "/api/channels/Dev%20%3E%20Rust/move")[0]?.body).toEqual({ parent: "" });
  });

  it("deletes a category", async () => {
    const { user } = mount(world(), "/categories");
    await user.click(await screen.findByRole("button", { name: "Delete Dev > Rust" }));
    await waitFor(() => {
      expect(screen.queryByRole("button", { name: "Edit Dev > Rust" })).not.toBeInTheDocument();
    });
  });

  it("shows only the latest refusal", async () => {
    const backend = world();
    const { user } = mount(backend, "/categories");
    const form = await screen.findByRole("form", { name: "Add a category" });
    backend.failWith = { status: 409, detail: "the category 'AI' is fed by blog: change those sources first" };
    await user.click(screen.getByRole("button", { name: "Delete AI" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("fed by blog");
    backend.failWith = { status: 409, detail: "a category named 'rust' already exists" };
    await user.type(within(form).getByLabelText("New category"), "rust");
    await user.click(within(form).getByRole("button", { name: "Add category" }));
    await waitFor(() => {
      expect(screen.getByRole("alert")).toHaveTextContent("already exists");
    });
    expect(within(form).getByLabelText("New category")).toHaveValue("rust");
  });

  it("offers to file existing items right after a category is created, and files them on request", async () => {
    const backend = world();
    backend.refiled = { filed: 2, queued: 5 };
    const { user } = mount(backend, "/categories");
    await user.click(await screen.findByRole("button", { name: "+ Security" }));
    const offer = await screen.findByRole("note");
    expect(offer).toHaveTextContent("7 items you already have could move: 2 by rule, 5 to be read again");
    expect(calls(backend, "POST", "/api/refile?dry_run=true")).toHaveLength(1);
    expect(calls(backend, "POST", "/api/refile?dry_run=false")).toHaveLength(0);
    await user.click(within(offer).getByRole("button", { name: "File them now" }));
    await waitFor(() => {
      expect(screen.queryByRole("note")).not.toBeInTheDocument();
    });
    expect(calls(backend, "POST", "/api/refile?dry_run=false")).toHaveLength(1);
    expect(screen.getByText(/Filed 2 by rule\. 5 will be read again/)).toBeInTheDocument();
  });

  it("lets the offer go when you say not now, and stays quiet when nothing could move", async () => {
    const backend = world();
    backend.refiled = { filed: 0, queued: 1 };
    const { user } = mount(backend, "/categories");
    await user.click(await screen.findByRole("button", { name: "+ Security" }));
    await user.click(await screen.findByRole("button", { name: "Not now" }));
    expect(screen.queryByRole("note")).not.toBeInTheDocument();
    backend.refiled = { filed: 0, queued: 0 };
    await user.click(screen.getByRole("button", { name: "+ Cloud" }));
    await screen.findByRole("button", { name: "Edit Cloud" });
    expect(screen.queryByRole("note")).not.toBeInTheDocument();
  });

  it("files existing items again by hand, and says what will happen", async () => {
    const backend = world();
    const { user } = mount(backend, "/categories");
    await user.click(await screen.findByRole("button", { name: "File existing items again" }));
    expect(await screen.findByText(/Filed 2 by rule\. 5 will be read again by the model/)).toBeInTheDocument();
    expect(calls(backend, "POST", "/api/refile?dry_run=false")).toHaveLength(1);
  });

  it("shows when filing again fails", async () => {
    const backend = world();
    const { user } = mount(backend, "/categories");
    const button = await screen.findByRole("button", { name: "File existing items again" });
    backend.failWith = { status: 500, detail: "disk full" };
    await user.click(button);
    expect(await screen.findByRole("alert")).toHaveTextContent("disk full");
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
