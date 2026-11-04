import { test, expect } from '@playwright/test'
import fs from 'node:fs'
import path from 'node:path'

/**
 * A read-only (grandparent) account must not be shown controls it can't use,
 * nor any private area. Needs LP_RO_USER / LP_RO_PASS (scripts/eval_ui.sh
 * creates a throwaway read-only user); skipped otherwise.
 *
 * Logs in through the UI so claims arrive AFTER the bundle loads (the order
 * that previously hid/showed the wrong controls).
 */
const RO_USER = process.env.LP_RO_USER
const RO_PASS = process.env.LP_RO_PASS
const OUT = path.resolve('eval-results')

test.describe('Read-only account', () => {
  test.skip(!RO_USER, 'LP_RO_USER not set')

  // The backend throttles logins (10 / 5 min per IP+user), so log in ONCE per
  // project through the API and reuse the cookie. The SPA still resolves the
  // role AFTER its bundle has loaded (GET /api/auth/me), which is the order
  // that matters for the module-level-role bug.
  let cookies = []
  test.beforeAll(async ({ browser, baseURL }) => {
    const ctx = await browser.newContext({ baseURL })
    const res = await ctx.request.post('/api/auth/login', { data: { username: RO_USER, password: RO_PASS } })
    expect(res.ok(), `readonly API login failed: ${res.status()}`).toBeTruthy()
    cookies = await ctx.cookies()
    await ctx.close()
  })

  async function login(page) {
    await page.context().addCookies(cookies)
    await page.goto('/')
    await expect(page.getByRole('heading', { name: 'Profiles' })).toBeVisible()
  }

  // Controls that mutate data. A readonly user must not be able to USE any
  // (hidden, disabled, or the page's `.write-action` greyed-out + pointer-events:none).
  const WRITE_LABELS = [
    /^\+ New Profile/, /Sync Milestones/, /Archive \/ Download Backup/, /Delete Profile/,
    /^\+ Milestone/, /^\+ Event/, /^\+ Note/, /^\+ New Lesson/, /Add this age group/, /Remove this age group/,
    /Save Note/, /Save Reflection/,
  ]

  async function usableWriteControls(page) {
    return page.evaluate((labels) => {
      const res = labels.map((l) => new RegExp(l[0], l[1]))
      const out = []
      for (const el of document.querySelectorAll('button, input[type=submit], [role=button]')) {
        const text = (el.textContent || '').trim()
        if (!res.some((r) => r.test(text))) continue
        const r = el.getBoundingClientRect()
        const cs = getComputedStyle(el)
        const visible = r.width > 0 && r.height > 0 && cs.visibility !== 'hidden' && cs.display !== 'none'
        const inert = el.disabled || cs.pointerEvents === 'none'
        if (visible && !inert) out.push(text.slice(0, 40))
      }
      return out
    }, WRITE_LABELS.map((r) => [r.source, r.flags]))
  }

  test('sees the dashboard but no create/delete controls', async ({ page }, ti) => {
    await login(page)
    await expect(page.getByText('Test Child').first()).toBeVisible()
    expect(await usableWriteControls(page), 'usable write controls on dashboard').toEqual([])
    await expect(page.getByRole('button', { name: /New Profile/ })).toHaveCount(0)
    fs.mkdirSync(OUT, { recursive: true })
    await page.screenshot({ path: path.join(OUT, `${ti.project.name}-readonly-dashboard.png`) })
  })

  test('profile view: no admin controls, private sections not offered', async ({ page }, ti) => {
    await login(page)
    await page.locator('a[href^="/profile/"]').first().click()
    await expect(page.getByRole('heading', { name: 'Development Pillars' })).toBeVisible()
    expect(await usableWriteControls(page), 'usable write controls on profile').toEqual([])
    await expect(page.getByRole('button', { name: /Delete Profile/ })).toHaveCount(0)
    // Role flag must be live in the DOM for CSS to grey out stragglers.
    expect(await page.evaluate(() => document.documentElement.getAttribute('data-role'))).toBe('readonly')
    fs.mkdirSync(OUT, { recursive: true })
    await page.screenshot({ path: path.join(OUT, `${ti.project.name}-readonly-profile.png`) })
  })

  test('bounty board: no edit/delete/status controls, no private ledgers', async ({ page }, ti) => {
    test.setTimeout(60_000)
    await login(page)
    await page.locator('a[href^="/profile/"]').first().click()
    await page.getByRole('button', { name: /Bounty Board/ }).first().click()
    await expect(page.getByText(/Adopt-a-Space|Broken Window Repair/).first()).toBeVisible()
    // Row-level actions: edit (✎) and delete (×) must not exist for readonly.
    await expect(page.locator('button[title="Edit"]')).toHaveCount(0)
    await expect(page.locator('.bounty-row button', { hasText: '×' })).toHaveCount(0)
    // Status dot must not be a clickable button (it renders a plain span).
    await expect(page.locator('.bounty-row button[title*="click to advance"]')).toHaveCount(0)
    // Private areas.
    await expect(page.getByText(/Behavior Incidents/i)).toHaveCount(0)
    await expect(page.getByText(/Earnings Summary|TOTAL EARNED/i)).toHaveCount(0)
    fs.mkdirSync(OUT, { recursive: true })
    await page.screenshot({ path: path.join(OUT, `${ti.project.name}-readonly-bounty.png`) })
  })

  test('discernment journal is not offered at all', async ({ page }) => {
    await login(page)
    await page.locator('a[href^="/profile/"]').first().click()
    await expect(page.getByRole('heading', { name: 'Development Pillars' })).toBeVisible()
    // The whole section (and its 10 category cards) is hidden from readonly.
    await expect(page.getByRole('heading', { name: 'Discernment & Reflections' })).toHaveCount(0)
    for (const cat of ['Health', 'Math', 'Science', 'Civics', 'Relationships', 'Faith', 'Tradition', 'Law', 'Network', 'Calling']) {
      await expect(page.locator('button', { hasText: new RegExp(`^\\S+${cat}Discernment`) })).toHaveCount(0)
    }
  })
})
