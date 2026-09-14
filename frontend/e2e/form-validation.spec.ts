import { test, expect } from "@playwright/test";
import path from "path";

const DISALLOWED_FILE = path.join(__dirname, "fixtures/disallowed.exe");

// Client-side validation never reaches the network, so this never touches
// the ticket_create throttle — safe to run any number of times.
test.describe("incident report form validation", () => {
  test("required fields are validated before submission", async ({ page }) => {
    await page.goto("/");
    await page.getByRole("button", { name: "File report" }).click();

    await expect(page.getByText("Enter your name.")).toBeVisible();
    await expect(page.getByText("Enter your email.")).toBeVisible();
    await expect(page.getByText("Enter a subject.")).toBeVisible();
    await expect(page.getByText("Select a category.")).toBeVisible();
    await expect(page.getByText("Describe what happened.")).toBeVisible();
  });

  test("an invalid email is rejected before submission", async ({ page }) => {
    await page.goto("/");
    await page.fill("#email", "not-an-email");
    await page.getByRole("button", { name: "File report" }).click();
    await expect(page.getByText("Enter a valid email address.")).toBeVisible();
  });

  test("the dropzone rejects a disallowed file type before upload", async ({ page }) => {
    await page.goto("/");
    await page.setInputFiles("#attachments", DISALLOWED_FILE);
    await expect(page.getByText(/is not an allowed file type/)).toBeVisible();
  });
});
