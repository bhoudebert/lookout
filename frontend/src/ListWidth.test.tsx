import { fireEvent, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { clampWidth, DEFAULT_WIDTH, MAX_WIDTH, MIN_WIDTH, readListWidth, rememberListWidth } from "./listWidth";
import { FakeBackend, makeItem } from "./test/fakeBackend";
import { mount } from "./test/render";

beforeEach(() => {
  window.localStorage.clear();
});
afterEach(() => {
  vi.unstubAllGlobals();
});

const news = () => [makeItem({ id: "a", title: "Quake in Chile" }), makeItem({ id: "b", title: "Chip merger" })];

/** The inbox with one item open, so the list has a reader beside it. */
async function opened() {
  const view = mount(new FakeBackend(news()));
  await view.user.click(await screen.findByRole("button", { name: "Quake in Chile" }));
  return { ...view, bar: await screen.findByRole("separator", { name: "List width" }) };
}
const columns = (): HTMLElement => document.querySelector<HTMLElement>(".columns") as HTMLElement;

describe("the width of the list", () => {
  it("is wider than before by default", async () => {
    const { bar } = await opened();
    expect(bar).toHaveAttribute("aria-valuenow", String(DEFAULT_WIDTH));
    expect(columns().style.getPropertyValue("--list-w")).toBe(`${String(DEFAULT_WIDTH)}px`);
  });

  it("is not offered when there is no reader beside the list", async () => {
    mount(new FakeBackend([]));
    await screen.findByText(/Nothing to look at/);
    expect(screen.queryByRole("separator")).not.toBeInTheDocument();
  });

  it("follows the mouse while the bar is dragged, within limits, and is remembered", async () => {
    const { bar } = await opened();
    fireEvent.mouseDown(bar, { clientX: 500 });
    fireEvent.mouseMove(window, { clientX: 560 });
    expect(bar).toHaveAttribute("aria-valuenow", String(DEFAULT_WIDTH + 60));
    fireEvent.mouseMove(window, { clientX: 5000 });
    expect(bar).toHaveAttribute("aria-valuenow", String(MAX_WIDTH));
    fireEvent.mouseUp(window);
    fireEvent.mouseMove(window, { clientX: 0 });
    expect(bar).toHaveAttribute("aria-valuenow", String(MAX_WIDTH));
    expect(readListWidth()).toBe(MAX_WIDTH);
  });

  it("moves with the arrow keys, goes to the ends, and comes back to the default", async () => {
    const { user, bar } = await opened();
    bar.focus();
    await user.keyboard("{ArrowRight}");
    expect(bar).toHaveAttribute("aria-valuenow", String(DEFAULT_WIDTH + 24));
    await user.keyboard("{Shift>}{ArrowLeft}{/Shift}");
    expect(bar).toHaveAttribute("aria-valuenow", String(DEFAULT_WIDTH + 24 - 96));
    await user.keyboard("{Home}");
    expect(bar).toHaveAttribute("aria-valuenow", String(MIN_WIDTH));
    await user.keyboard("{End}");
    expect(bar).toHaveAttribute("aria-valuenow", String(MAX_WIDTH));
    await user.keyboard("{Enter}");
    expect(bar).toHaveAttribute("aria-valuenow", String(DEFAULT_WIDTH));
    await user.keyboard("{Shift>}{ArrowRight}{/Shift}{a}");
    expect(bar).toHaveAttribute("aria-valuenow", String(DEFAULT_WIDTH + 96));
    await user.dblClick(bar);
    expect(bar).toHaveAttribute("aria-valuenow", String(DEFAULT_WIDTH));
  });

  it("cannot be touched while a dialog is open, and a drag in progress ends", async () => {
    const { user, bar } = await opened();
    fireEvent.mouseDown(bar, { clientX: 500 });
    fireEvent.mouseMove(window, { clientX: 540 });
    expect(bar).toHaveAttribute("aria-valuenow", String(DEFAULT_WIDTH + 40));

    await user.keyboard("?");
    expect(await screen.findByRole("dialog", { name: "Keyboard shortcuts" })).toBeInTheDocument();
    expect(bar).toHaveAttribute("aria-disabled", "true");
    expect(bar).toHaveAttribute("tabindex", "-1");
    fireEvent.mouseMove(window, { clientX: 700 });
    fireEvent.mouseDown(bar, { clientX: 500 });
    fireEvent.mouseMove(window, { clientX: 700 });
    fireEvent.keyDown(bar, { key: "End" });
    fireEvent.doubleClick(bar);
    expect(bar).toHaveAttribute("aria-valuenow", String(DEFAULT_WIDTH + 40));

    await user.keyboard("{Escape}");
    expect(bar).toHaveAttribute("aria-disabled", "false");
    fireEvent.keyDown(bar, { key: "Home" });
    expect(bar).toHaveAttribute("aria-valuenow", String(MIN_WIDTH));
  });

  it("is back where it was left at the next visit", async () => {
    rememberListWidth(600);
    const { bar } = await opened();
    expect(bar).toHaveAttribute("aria-valuenow", "600");
  });
});

describe("the remembered width", () => {
  it("stays within limits", () => {
    expect(clampWidth(10)).toBe(MIN_WIDTH);
    expect(clampWidth(99_999)).toBe(MAX_WIDTH);
    rememberListWidth(99_999);
    expect(readListWidth()).toBe(MAX_WIDTH);
  });

  it("copes with storage that cannot be used", () => {
    vi.stubGlobal("localStorage", {
      getItem: () => {
        throw new Error("blocked");
      },
      setItem: () => {
        throw new Error("blocked");
      },
    });
    expect(readListWidth()).toBe(DEFAULT_WIDTH);
    expect(() => {
      rememberListWidth(500);
    }).not.toThrow();
  });
});
