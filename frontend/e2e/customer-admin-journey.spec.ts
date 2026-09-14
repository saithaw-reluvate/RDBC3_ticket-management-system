import { test, expect } from "@playwright/test";
import path from "path";
import { extractTrackingToken, findEmailBySubjectFragment } from "./helpers/mailpit";
import { loadFixtures } from "./helpers/fixtures";

const EVIDENCE_PDF = path.join(__dirname, "fixtures/evidence.pdf");
const RUN_ID = Date.now();
const CUSTOMER_EMAIL = `e2e.journey.${RUN_ID}@example.com`;
const REPORTER_NAME = "E2E Journey Customer";
const SUBJECT = `E2E journey ticket ${RUN_ID}`;
const PUBLIC_REPLY = "Thanks for the report — we can reproduce this and are on it.";
const INTERNAL_NOTE = "E2E: internal-only note, must never reach the customer.";

// One continuous, stateful journey through the real system: public
// submission -> real Mailpit email -> customer tracking -> admin
// management -> customer-visible effects of admin actions -> link
// lifecycle -> sign-out. A single test with test.step() stages —
// deliberately NOT split into separate test() cases, because Playwright
// gives every test() its own browser context (and therefore its own
// cookie jar) by default even inside describe.serial, which would silently
// drop the admin session between "stages". One test == one shared page/
// context == the session and the ticket reference stay valid throughout,
// matching what an actual admin session looks like.
test("customer + admin full journey", async ({ page }) => {
  let reference = "";
  let initialToken = "";
  let resentToken = "";

  await test.step("customer submits an incident with an attachment", async () => {
    await page.goto("/");
    await page.fill("#reporter_name", REPORTER_NAME);
    await page.fill("#email", CUSTOMER_EMAIL);
    await page.fill("#subject", SUBJECT);
    await page.selectOption("#category", "BUG");
    await page.fill("#description", "Seeded by the Step 4 E2E journey test.");
    await page.setInputFiles("#attachments", EVIDENCE_PDF);
    await page.getByRole("button", { name: "File report" }).click();

    await page.waitForURL(/\/submitted\//);
    reference = new URL(page.url()).pathname.split("/").pop()!;
    expect(reference).toMatch(/^TKT-[A-Z0-9]{8}$/);

    await expect(page.getByText("Filed.")).toBeVisible();
    await expect(page.getByText(CUSTOMER_EMAIL)).toBeVisible();
    // Decision 1: the receipt must never carry a real tracking link — the
    // only /track/ href allowed here is the static "request a new link" CTA.
    const trackHrefs = await page
      .locator('a[href^="/track/"]')
      .evaluateAll((els) => els.map((el) => el.getAttribute("href")));
    expect(trackHrefs.every((href) => href === "/track/link")).toBe(true);
  });

  await test.step("the creation email arrives with a working tracking link", async () => {
    const email = await findEmailBySubjectFragment(`[${reference}] We received your ticket`);
    initialToken = extractTrackingToken(email.text);
    expect(initialToken).toBeTruthy();

    await page.goto(`/track/${initialToken}/`);
    await expect(page.locator("h1")).toHaveText(SUBJECT);
    await expect(page.getByText(reference)).toBeVisible();
    await expect(page.getByText("evidence.pdf")).toBeVisible();
  });

  await test.step("customer can download their own attachment", async () => {
    await page.goto(`/track/${initialToken}/`);
    const [download] = await Promise.all([
      page.waitForEvent("download"),
      page.getByText("evidence.pdf").click(),
    ]);
    expect(download.suggestedFilename()).toBe("evidence.pdf");
  });

  await test.step("invalid and expired tokens are distinguished from a valid one", async () => {
    await page.goto("/track/not-a-real-token-at-all/");
    await expect(page.locator("h1")).toHaveText("We couldn't find this report.");

    const { expiredToken } = loadFixtures();
    await page.goto(`/track/${expiredToken}/`);
    await expect(page.locator("h1")).toHaveText("This link has expired.");
  });

  await test.step("admin routes redirect to login while signed out", async () => {
    await page.goto("/admin");
    await page.waitForURL(/\/admin\/login/);

    await page.goto(`/admin/tickets/${reference}`);
    await page.waitForURL(/\/admin\/login/);
  });

  await test.step("a wrong admin password is rejected without revealing which field", async () => {
    const { adminUsername } = loadFixtures();
    await page.goto("/admin/login");
    await page.fill("#username", adminUsername);
    await page.fill("#password", "definitely-the-wrong-password");
    await page.getByRole("button", { name: "Sign in" }).click();
    await expect(page.getByText("Those credentials weren't recognised")).toBeVisible();
  });

  await test.step("admin signs in and finds the ticket via search", async () => {
    const { adminUsername, adminPassword } = loadFixtures();
    await page.goto("/admin/login");
    await page.fill("#username", adminUsername);
    await page.fill("#password", adminPassword);
    await page.getByRole("button", { name: "Sign in" }).click();
    await page.waitForURL(/\/admin$/);

    await page.getByLabel("Search tickets").fill(reference);
    await page.getByText(reference, { exact: true }).click();
    await page.waitForURL(new RegExp(`/admin/tickets/${reference}`));
    await expect(page.locator("h1")).toHaveText(SUBJECT);
  });

  await test.step("admin changes status, priority and category, and they persist", async () => {
    // Each select's onChange fires an uncounted PATCH; selectOption() only
    // waits for the DOM 'change' event, not that async request. Waiting for
    // the matching response before the next change (and before reload)
    // avoids the browser aborting a still-in-flight PATCH on navigation.
    const waitForPatch = () =>
      page.waitForResponse(
        (res) =>
          res.url().includes(`/api/admin/tickets/${reference}/`) &&
          res.request().method() === "PATCH" &&
          res.status() === 200
      );

    await Promise.all([waitForPatch(), page.selectOption("#status-select", "IN_PROGRESS")]);
    await expect(page.locator("#status-select")).toHaveValue("IN_PROGRESS");

    await Promise.all([waitForPatch(), page.selectOption("#priority-select", "HIGH")]);
    await expect(page.locator("#priority-select")).toHaveValue("HIGH");

    await Promise.all([waitForPatch(), page.selectOption("#category-select", "SECURITY")]);
    await expect(page.locator("#category-select")).toHaveValue("SECURITY");

    // Optimistic UI updates immediately; reload to confirm it actually
    // persisted server-side rather than only in local state.
    await page.reload();
    await expect(page.locator("#status-select")).toHaveValue("IN_PROGRESS");
    await expect(page.locator("#priority-select")).toHaveValue("HIGH");
    await expect(page.locator("#category-select")).toHaveValue("SECURITY");
  });

  await test.step("admin downloads the customer's attachment", async () => {
    const [download] = await Promise.all([
      page.waitForEvent("download"),
      page.getByText("evidence.pdf").click(),
    ]);
    expect(download.suggestedFilename()).toBe("evidence.pdf");
  });

  await test.step("a public reply reaches the customer's inbox and ticket page", async () => {
    await page.getByRole("button", { name: "Public reply", exact: true }).click();
    await page.fill("#composer-message", PUBLIC_REPLY);
    await page.getByRole("button", { name: "Send reply", exact: true }).click();
    await expect(page.getByText("Reply sent.")).toBeVisible();
    await expect(page.getByText(PUBLIC_REPLY)).toBeVisible();

    await findEmailBySubjectFragment(`[${reference}] New response`);

    await page.goto(`/track/${initialToken}/`);
    await expect(page.getByText(PUBLIC_REPLY)).toBeVisible();
  });

  await test.step("an internal note never reaches the customer", async () => {
    await page.goto(`/admin/tickets/${reference}`);
    await page.getByRole("button", { name: "Internal note", exact: true }).click();
    await expect(page.getByText("Visible to staff only")).toBeVisible();
    await page.fill("#composer-message", INTERNAL_NOTE);
    await page.getByRole("button", { name: "Add internal note", exact: true }).click();
    await expect(page.getByText("Internal note added.")).toBeVisible();
    await expect(page.getByText(INTERNAL_NOTE)).toBeVisible(); // visible to the admin

    await page.goto(`/track/${initialToken}/`);
    // innerText (not textContent) — must never appear even inside the RSC
    // hydration payload, not just outside visible text.
    expect(await page.locator("body").innerText()).not.toContain(INTERNAL_NOTE);
    expect(await page.content()).not.toContain(INTERNAL_NOTE);
  });

  await test.step("resend-link mints a working new link without revoking the old one", async () => {
    await page.goto(`/admin/tickets/${reference}`);
    await page.getByRole("button", { name: "Resend link", exact: true }).click();
    await expect(page.getByText("Tracking link resent.")).toBeVisible();

    const email = await findEmailBySubjectFragment(`[${reference}] Your tracking link`);
    resentToken = extractTrackingToken(email.text);
    expect(resentToken).not.toBe(initialToken);

    await page.goto(`/track/${resentToken}/`);
    await expect(page.locator("h1")).toHaveText(SUBJECT);
    await page.goto(`/track/${initialToken}/`);
    await expect(page.locator("h1")).toHaveText(SUBJECT);
  });

  await test.step("revoke-links invalidates every active link for the ticket", async () => {
    await page.goto(`/admin/tickets/${reference}`);
    await page.getByRole("button", { name: "Revoke links", exact: true }).click();
    await page.getByRole("button", { name: "Revoke", exact: true }).click();
    await expect(page.getByText(/Revoked \d+ tracking link/)).toBeVisible();

    await page.goto(`/track/${initialToken}/`);
    await expect(page.locator("h1")).toHaveText("This link has been replaced.");
    await page.goto(`/track/${resentToken}/`);
    await expect(page.locator("h1")).toHaveText("This link has been replaced.");
  });

  await test.step("logout ends the session and protected routes redirect again", async () => {
    await page.goto(`/admin/tickets/${reference}`);
    await page.getByRole("button", { name: "Log out", exact: true }).click();
    await page.waitForURL(/\/admin\/login/);

    await page.goto("/admin");
    await page.waitForURL(/\/admin\/login/);
  });
});
