import { defineConfig, devices } from '@playwright/test'

/**
 * Playwright config for the Life Plan Tracker.
 *
 * The full app (API + built frontend) is served by the FastAPI backend on
 * http://localhost:8000. These tests assume that server is already running
 * (start it with `app/backend/start_server.sh`). The frontend must be built
 * (`npm run build`) so the backend serves the current bundle.
 */
export default defineConfig({
  testDir: './tests',
  // a11y + walkthrough are read-only; safe to keep serial for clear reporting
  fullyParallel: false,
  workers: 1,
  reporter: [['list'], ['html', { open: 'never', outputFolder: 'playwright-report' }]],
  timeout: 30_000,
  expect: { timeout: 10_000 },
  use: {
    baseURL: process.env.LP_BASE_URL || 'http://localhost:8000',
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
  },
  projects: [
    { name: 'chromium', use: { ...devices['Desktop Chrome'] } },
  ],
})
