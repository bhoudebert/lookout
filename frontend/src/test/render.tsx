import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { vi } from "vitest";
import { App } from "../App";
import type { FakeBackend } from "./fakeBackend";

/** Mount the whole app at ``url`` against a fake backend. */
export function mount(backend: FakeBackend, url = "/") {
  vi.stubGlobal("fetch", backend.fetch);
  window.history.replaceState(null, "", url);
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  const user = userEvent.setup();
  const view = render(
    <QueryClientProvider client={client}>
      <App />
    </QueryClientProvider>,
  );
  return { user, client, ...view };
}
