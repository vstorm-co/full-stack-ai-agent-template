import { test as setup, expect } from "@playwright/test";
import path from "path";

const authFile = path.join(__dirname, "../.playwright/.auth/user.json");

/**
 * Authentication setup - runs before all tests.
 *
 * This creates an authenticated session that other tests can reuse.
 */
setup("authenticate", async ({ page }) => {
  // Test credentials - adjust for your environment
  const testEmail = process.env.TEST_USER_EMAIL || "test@example.com";
  const testPassword = process.env.TEST_USER_PASSWORD || "TestPassword123!";

  // Navigate to login page
  await page.goto("/login");

  // Fill in login form
  await page.getByLabel(/email/i).fill(testEmail);
  await page.getByLabel(/password/i).fill(testPassword);

  // Submit and wait for redirect
  await page.getByRole("button", { name: /sign in|log in|login/i }).click();

  // Wait for authentication to complete - adjust selector based on your app
  await expect(
    page.getByRole("link", { name: /dashboard|home/i }).or(page.getByText(/welcome/i)),
  ).toBeVisible({ timeout: 10000 });

  // Save authentication state
  await page.context().storageState({ path: authFile });
});
