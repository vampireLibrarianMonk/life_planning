import { test, expect } from '@playwright/test'
import { loginAsAdmin, openFirstProfile } from './helpers.js'

/**
 * End-to-end walkthrough: logs in, opens a profile, and verifies the major
 * sections render — including the Programs view with the newly added
 * Just War Ethics and City of God programs, and the 311 civic bounties.
 *
 * Read-only: no data is created or mutated.
 */

test.describe('Life Plan Tracker walkthrough', () => {
  test('login screen renders with accessible form', async ({ page }) => {
    await page.goto('/')
    await expect(page.getByRole('heading', { name: 'Life Plan Tracker' })).toBeVisible()
    await expect(page.getByLabel('Username')).toBeVisible()
    await expect(page.getByLabel('Password')).toBeVisible()
    await expect(page.getByRole('button', { name: 'Login' })).toBeVisible()
  })

  test('admin can log in and reach the dashboard', async ({ page }) => {
    await loginAsAdmin(page)
    await expect(page.getByRole('heading', { name: 'Profiles' })).toBeVisible()
  })

  test('profile view shows the core sections', async ({ page }) => {
    await loginAsAdmin(page)
    await openFirstProfile(page)
    for (const heading of ['Roadmap', 'Development Pillars', 'Programs, Career & Economy', 'Discernment & Reflections']) {
      await expect(page.getByRole('heading', { name: heading })).toBeVisible()
    }
  })

  test('development pillars are present and openable', async ({ page }) => {
    await loginAsAdmin(page)
    await openFirstProfile(page)
    const pillarsHeading = page.getByRole('heading', { name: 'Development Pillars' })
    await expect(pillarsHeading).toBeVisible()
    // Pillar cards are buttons inside the .pillar-grid-desktop container.
    const firstPillar = page.locator('.pillar-grid-desktop button').first()
    await expect(firstPillar).toBeVisible()
    await firstPillar.click()
    await expect(page.getByRole('button', { name: /Back to Dashboard/ })).toBeVisible()
    await page.getByRole('button', { name: /Back to Dashboard/ }).click()
    // Confirm we returned to the dashboard-level profile view.
    await expect(page.getByRole('heading', { name: 'Development Pillars' })).toBeVisible()
  })

  test('programs view lists all tracks including the two new Augustinian programs', async ({ page }) => {
    await loginAsAdmin(page)
    await openFirstProfile(page)
    await page.getByRole('button', { name: /Programs/ }).first().click()
    await expect(page.getByRole('button', { name: /Back to Dashboard/ })).toBeVisible()
    // New programs added in this integration:
    await expect(page.getByText('Just War Ethics', { exact: false })).toBeVisible()
    await expect(page.getByText('City of God', { exact: false })).toBeVisible()
    // A representative existing program should still be present:
    await expect(page.getByText('311 Civic Service', { exact: false })).toBeVisible()
  })

  test('bounty board opens and shows civic-sense commons bounties', async ({ page }) => {
    await loginAsAdmin(page)
    await openFirstProfile(page)
    await page.getByRole('button', { name: /Bounty Board/ }).first().click()
    await expect(page.getByRole('button', { name: /Back to Dashboard/ })).toBeVisible()
    // One of the six new 311 bounties should be discoverable in the board.
    await expect(page.getByText(/Adopt-a-Space|Broken Window Repair|Be the Change/).first()).toBeVisible()
  })
})
