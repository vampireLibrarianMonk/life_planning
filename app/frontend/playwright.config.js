import { defineConfig, devices } from '@playwright/test'

/**
 * Playwright config for the Life Plan Tracker.
 *
 * The full app (API + built frontend) is served by the FastAPI backend on
 * http://localhost:8000. These tests assume that server is already running
 * (start it with `app/backend/start_server.sh`, or use `npm run test:eval`
 * from the repo root script `scripts/eval_ui.sh`, which boots an isolated
 * server for you). The frontend must be built (`npm run build`).
 *
 * Projects run the device evaluation in desktop and mobile modes. iPhones run in
 * WebKit (the engine Safari uses); Android phones run in Chromium. Caveat: this is
 * Playwright's Linux WebKit build with an iOS user agent and device metrics, NOT
 * real iOS Safari. It matches Safari's engine family, but not iOS-specific behaviour
 * (dynamic toolbar, safe-area insets, keyboard, pinch/zoom). Do a final check on a
 * real iPhone.
 *
 * The breakpoint is 767px (see src/services/device.js + index.html), so the
 * 768 project sits exactly one pixel on the desktop side of it.
 *
 * WebKit on Linux needs system libraries: run `sudo npx playwright install-deps webkit`.
 */
// Mobile projects run the device evaluation and the read-only account checks.
const EVAL_ONLY = /(device_eval|readonly_ui)\.spec\.js/

// Playwright 1.55 has no iPhone 16 profile. Built from the iPhone 15 profile
// (same Safari viewport chrome) with the iPhone 16's 393x852 point screen and iOS 18.
const iPhone16 = {
  ...devices['iPhone 15'],
  screen: { width: 393, height: 852 },
  userAgent:
    'Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.0 Mobile/15E148 Safari/604.1',
}

export default defineConfig({
  testDir: './tests',
  // a11y + walkthrough + eval are read-only; safe to keep serial for clear reporting
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
    // Desktop runs EVERY spec (walkthrough, a11y, child-dev, device eval).
    { name: 'desktop', use: { ...devices['Desktop Chrome'] } },
    // Mobile/boundary projects run only the device evaluation, so the full
    // suites aren't multiplied across devices (and logins stay under the
    // backend's login throttle).
    { name: 'iphone-16', testMatch: EVAL_ONLY, use: iPhone16 },
    { name: 'iphone-15-pro-max', testMatch: EVAL_ONLY, use: devices['iPhone 15 Pro Max'] },
    { name: 'iphone-se', testMatch: EVAL_ONLY, use: devices['iPhone SE'] },
    { name: 'galaxy-s24', testMatch: EVAL_ONLY, use: devices['Galaxy S24'] },
    { name: 'pixel-7', testMatch: EVAL_ONLY, use: devices['Pixel 7'] },
    // Exactly one px above the breakpoint: must get the DESKTOP layout.
    {
      name: 'tablet-768',
      testMatch: EVAL_ONLY,
      use: { ...devices['Desktop Chrome'], viewport: { width: 768, height: 1024 }, hasTouch: true },
    },
  ],
})
