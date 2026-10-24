import { defineConfig, devices } from "@playwright/test";

// The journeys drive the real backend (SQLite, scheduler off) serving the built dashboard, with a fake feed and a
// fake model on port 8902. One worker, in order: the journeys share one database, like a person using one inbox.
const PORT = 8899;
const CONFIG = "frontend/e2e/lookout.yaml";

export default defineConfig({
  testDir: "e2e",
  fullyParallel: false,
  workers: 1,
  retries: 0,
  reporter: [["list"], ["html", { open: "never" }]],
  use: { baseURL: `http://127.0.0.1:${PORT}`, trace: "retain-on-failure", screenshot: "only-on-failure" },
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],
  webServer: [
    {
      command: "node frontend/e2e/world.mjs",
      cwd: "..",
      url: "http://127.0.0.1:8902/v1/models",
      reuseExistingServer: false,
    },
    {
      command: `sh -c "rm -f frontend/e2e/.data/e2e.db* && uv run lookout --config ${CONFIG} demo && uv run lookout --config ${CONFIG} serve --port ${PORT}"`,
      cwd: "..",
      url: `http://127.0.0.1:${PORT}/api/health`,
      reuseExistingServer: false,
      timeout: 60_000,
    },
  ],
});
