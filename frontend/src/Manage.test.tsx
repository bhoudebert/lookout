import { screen, waitFor, within } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { FakeBackend, makeSource } from "./test/fakeBackend";
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
  it("lists each source with its type, channels (or any), health and a way to manage it", async () => {
    mount(world(), "/sources");
    const blog = await screen.findByRole("row", { name: /blog/ });
    expect(blog).toHaveTextContent("rss");
    expect(blog).toHaveTextContent("AI");
    expect(screen.getByRole("row", { name: /gh/ })).toHaveTextContent("any");
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
    expect(screen.getByRole("row", { name: /blog/ })).toHaveTextContent("any");
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

describe("channels", () => {
  it("lists the channels with their descriptions", async () => {
    mount(world(), "/sources");
    const panel = await screen.findByRole("region", { name: "Channels" });
    expect(within(panel).getByText("Models")).toBeInTheDocument();
    expect(within(panel).getAllByText("no description")).toHaveLength(2);
  });

  it("adds a channel and empties the form", async () => {
    const backend = world();
    const { user } = mount(backend, "/sources");
    const form = await screen.findByRole("form", { name: "Add a channel" });
    await user.type(within(form).getByLabelText("New channel"), "Web");
    await user.type(within(form).getByLabelText("Description"), "Frontend");
    await user.click(within(form).getByRole("button", { name: "Add channel" }));
    expect(await screen.findByRole("button", { name: "Edit Web" })).toBeInTheDocument();
    expect(within(form).getByLabelText("New channel")).toHaveValue("");
    expect(calls(backend, "POST", "/api/channels")[0]?.body).toEqual({ name: "Web", description: "Frontend" });
    await user.click(await screen.findByRole("button", { name: "Add a source" }));
    expect(
      within(screen.getByRole("form", { name: "Add a source" })).getByRole("checkbox", { name: "Web" }),
    ).toBeInTheDocument();
  });

  it("changes a description, or cancels", async () => {
    const backend = world();
    const { user } = mount(backend, "/sources");
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

  it("deletes a channel", async () => {
    const backend = world();
    const { user } = mount(backend, "/sources");
    await user.click(await screen.findByRole("button", { name: "Delete Rust" }));
    await waitFor(() => {
      expect(screen.queryByRole("button", { name: "Edit Rust" })).not.toBeInTheDocument();
    });
  });

  it("shows why a channel cannot be added, changed or deleted", async () => {
    const backend = world();
    const { user } = mount(backend, "/sources");
    const form = await screen.findByRole("form", { name: "Add a channel" });
    backend.failWith = { status: 409, detail: "the channel 'AI' is fed by blog: change those sources first" };
    await user.click(screen.getByRole("button", { name: "Delete AI" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("fed by blog");
    backend.failWith = { status: 409, detail: "a channel named 'rust' already exists" };
    await user.type(within(form).getByLabelText("New channel"), "rust");
    await user.click(within(form).getByRole("button", { name: "Add channel" }));
    await waitFor(() => {
      expect(screen.getByRole("alert")).toHaveTextContent("already exists");
    });
    expect(within(form).getByLabelText("New channel")).toHaveValue("rust");
    await user.click(screen.getByRole("button", { name: "Edit Rust" }));
    backend.failWith = { status: 404, detail: "no such source or channel: Rust" };
    await user.click(screen.getByRole("button", { name: "Save" }));
    await waitFor(() => {
      expect(screen.getByRole("alert")).toHaveTextContent("no such source or channel");
    });
    expect(screen.getByLabelText("Description of Rust")).toBeInTheDocument();
  });
});
