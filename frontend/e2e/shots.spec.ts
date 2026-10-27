import { expect, test } from "@playwright/test";

// Screenshots for the website, taken from the real app on the demo data.
// Not part of the journeys: `npm run shots` starts a fresh server and sets SHOTS=1.
test.skip(!process.env.SHOTS, "only when making the website's screenshots");

// Where the screenshots go; a design proposal sets SHOTS_OUT to keep its own.
const OUT = process.env.SHOTS_OUT ?? "../site/shots";

test("the inbox", async ({ browser }) => {
  const context = await browser.newContext({ viewport: { width: 1200, height: 760 } });
  const page = await context.newPage();
  await page.goto("/");
  await expect(page.getByRole("list", { name: "Items" }).getByRole("listitem")).toHaveCount(6);
  await page.screenshot({ path: `${OUT}/inbox-light.png` });
  await context.close();
});

test("an item with the reason for its priority", async ({ browser }) => {
  const context = await browser.newContext({ viewport: { width: 1200, height: 760 } });
  const page = await context.newPage();
  await page.goto("/");
  await page.getByRole("button", { name: /^Django security releases/ }).click();
  await expect(page.getByRole("complementary", { name: "Item detail" })).toContainText("rule: critical advisory");
  await page.screenshot({ path: `${OUT}/detail-light.png` });
  await context.close();
});

test("the categories, as a tree", async ({ browser }) => {
  const context = await browser.newContext({ viewport: { width: 1200, height: 760 } });
  const page = await context.newPage();
  await page.goto("/categories");
  await expect(page.getByRole("region", { name: "Categories" })).toBeVisible();
  await page.screenshot({ path: `${OUT}/categories-light.png` });
  await context.close();
});
