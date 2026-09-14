import { test, expect } from "@playwright/test";

// Independent of the main journey: exercises the public, anonymous
// /track/link recovery form. Only 2 calls against the resend_link throttle
// (3/hour) — safe to run alongside the journey spec's own resend/revoke
// tests, which go through the separate, unthrottled admin endpoint.
test.describe("public tracking-link recovery", () => {
  test("known and unknown addresses get an identical response", async ({ page }) => {
    await page.goto("/track/link");
    await page.fill("#email", `e2e.recovery.known.${Date.now()}@example.com`);
    await page.getByRole("button", { name: "Send link" }).click();
    await expect(page.getByText("Check your inbox.")).toBeVisible();
    const knownCopy = await page.getByText(/tracking link has been sent/).textContent();

    await page.goto("/track/link");
    await page.fill("#email", `e2e.recovery.unknown.${Date.now()}@example.com`);
    await page.getByRole("button", { name: "Send link" }).click();
    await expect(page.getByText("Check your inbox.")).toBeVisible();
    const unknownCopy = await page.getByText(/tracking link has been sent/).textContent();

    expect(unknownCopy).toBe(knownCopy);
  });
});
