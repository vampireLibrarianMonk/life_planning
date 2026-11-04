import { test, expect } from '@playwright/test'
import { ADMIN_USER, ADMIN_PASS, openFirstProfile } from './helpers.js'

/**
 * Regression: Profile.jsx used to read the user's role when the module loaded
 * (before login claims existed), so `adminUser` was frozen at false and every
 * admin-only control (e.g. "Remove this age group") was hidden from admins.
 *
 * Log in through the UI (so the claims arrive AFTER the bundle has loaded,
 * which is exactly the real-world order) and check an admin-only control shows.
 */
test.describe('Role-dependent controls', () => {
  test('admin sees admin-only controls after logging in', async ({ page }) => {
    await page.goto('/')
    await page.getByLabel('Username').fill(ADMIN_USER)
    await page.getByLabel('Password').fill(ADMIN_PASS)
    await page.getByRole('button', { name: 'Login' }).click()
    await expect(page.getByRole('heading', { name: 'Profiles' })).toBeVisible()
    await openFirstProfile(page)

    await page.getByRole('button', { name: /Early Growth Markers/ }).click()
    await page.getByRole('button', { name: /~12 Months/ }).first().click()
    await expect(page.getByRole('heading', { name: '~12 Months' })).toBeVisible()
    const add = page.getByRole('button', { name: 'Add this age group' })
    if (await add.isVisible().catch(() => false)) await add.click()
    await expect(page.getByRole('button', { name: 'Remove this age group' })).toBeVisible()

    // Leave no residue.
    page.once('dialog', (d) => d.accept())
    await page.getByRole('button', { name: 'Remove this age group' }).click()
  })
})
