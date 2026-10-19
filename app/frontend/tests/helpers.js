import { expect } from '@playwright/test'

export const ADMIN_USER = process.env.LP_ADMIN_USER || 'admin'
export const ADMIN_PASS = process.env.LP_ADMIN_PASS || 'changeme'

/**
 * Log in as admin through the UI and land on the Dashboard.
 * Returns once at least one profile card (or the "New Profile" control) is visible.
 */
export async function loginAsAdmin(page) {
  await page.goto('/')
  await page.getByLabel('Username').fill(ADMIN_USER)
  await page.getByLabel('Password').fill(ADMIN_PASS)
  await page.getByRole('button', { name: 'Login' }).click()
  // Dashboard renders the "Profiles" section heading after auth.
  await expect(page.getByRole('heading', { name: 'Profiles' })).toBeVisible()
}

/**
 * Open the first profile card and wait for the profile view to render.
 */
export async function openFirstProfile(page) {
  const firstCard = page.locator('a[href^="/profile/"]').first()
  await expect(firstCard).toBeVisible()
  await firstCard.click()
  await expect(page.getByRole('heading', { name: 'Development Pillars' })).toBeVisible()
}
