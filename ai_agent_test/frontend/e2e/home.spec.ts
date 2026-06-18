import { test, expect } from "@playwright/test";

test.describe("Home Page", () => {
  test("should load the home page", async ({ page }) => {
    await page.goto("/");
    await expect(page).toHaveTitle(/ai_agent_test/i);
  });

  test("should have navigation elements", async ({ page }) => {
    await page.goto("/");

    // Check for main navigation elements
    const nav = page.getByRole("navigation");
    await expect(nav).toBeVisible();
  });

  test("should be accessible", async ({ page }) => {
    await page.goto("/");

    // Basic accessibility checks
    // Main landmark should exist
    await expect(page.getByRole("main")).toBeVisible();

    // Page should have a heading
    const heading = page.getByRole("heading", { level: 1 });
    await expect(heading).toBeVisible();
  });
});

test.describe("Navigation", () => {
  test("unauthenticated user should see login link", async ({ page }) => {
    // Clear any stored auth state
    await page.context().clearCookies();
    await page.goto("/");

    // Should have login/sign in link
    const loginLink = page.getByRole("link", { name: /log in|sign in/i });
    await expect(loginLink).toBeVisible();
  });

  test("should navigate between pages", async ({ page }) => {
    await page.goto("/");

    // Test navigation to different sections
    const links = await page.getByRole("link").all();
    expect(links.length).toBeGreaterThan(0);
  });
});

test.describe("Responsive Design", () => {
  test("should work on mobile viewport", async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 667 });
    await page.goto("/");

    // Page should still be functional
    await expect(page.getByRole("main")).toBeVisible();
  });

  test("should work on tablet viewport", async ({ page }) => {
    await page.setViewportSize({ width: 768, height: 1024 });
    await page.goto("/");

    // Page should still be functional
    await expect(page.getByRole("main")).toBeVisible();
  });
});
