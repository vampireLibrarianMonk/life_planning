import { test, expect } from '@playwright/test'
import { loginAsAdmin, openFirstProfile } from './helpers.js'

const CD_PROFILE_ID = process.env.LP_CD_PROFILE_ID || ''

async function openProfile(page) {
  if (CD_PROFILE_ID) {
    await page.goto(`/profile/${CD_PROFILE_ID}`)
    await expect(page.getByRole('heading', { name: 'Development Pillars' })).toBeVisible()
  } else {
    await openFirstProfile(page)
  }
}

/**
 * Child Development section end-to-end: open the section, activate an age group,
 * mark an objective, add a custom objective, and use the private worries note.
 * Cleans up after itself by removing the activated age group.
 */
test.describe('Child Development section', () => {
  test('appears on the dashboard just below Life Maps', async ({ page }) => {
    await loginAsAdmin(page)
    await openProfile(page)
    await expect(page.getByRole('heading', { name: 'Child Development' })).toBeVisible()
    await expect(page.getByRole('button', { name: /Early Growth Markers/ })).toBeVisible()
  })

  test('activate an age group, mark + add objectives, private worries, then clean up', async ({ page }) => {
    await loginAsAdmin(page)
    await openProfile(page)

    // Open the section.
    await page.getByRole('button', { name: /Early Growth Markers/ }).click()
    await expect(page.getByRole('heading', { name: 'Child Development' })).toBeVisible()

    // Open the ~12 Months group card.
    await page.getByRole('button', { name: /~12 Months/ }).first().click()
    await expect(page.getByRole('heading', { name: '~12 Months' })).toBeVisible()

    // Activate if needed, and wait for objectives to render.
    const addGroup = page.getByRole('button', { name: 'Add this age group' })
    if (await addGroup.isVisible().catch(() => false)) {
      await addGroup.click()
    }
    // A known 12mo objective should render under its domain (wait for seed+load).
    await expect(page.getByText('peekaboo or pat-a-cake', { exact: false })).toBeVisible({ timeout: 15000 })

    // Mark the first objective "practicing".
    await page.getByRole('button', { name: 'practicing' }).first().click()

    // Add a custom objective under the first domain.
    await page.getByRole('button', { name: '+ Add your own' }).first().click()
    await page.getByPlaceholder('Describe what to look for…').fill('E2E custom objective')
    await page.getByRole('button', { name: 'Add', exact: true }).click()
    await expect(page.getByText('E2E custom objective')).toBeVisible()

    // Private worries note is present and savable.
    await expect(page.getByText('Questions & worries for the next check-up')).toBeVisible()
    await page.getByPlaceholder(/Keep sensitive concerns here/).fill('E2E: just checking the private note')
    await page.getByRole('button', { name: 'Save' }).click()
    await expect(page.getByRole('button', { name: /Saved/ })).toBeVisible()

    // Clean up: remove the age group (admin-only button).
    page.once('dialog', d => d.accept())
    await page.getByRole('button', { name: 'Remove this age group' }).click()
    await expect(page.getByRole('heading', { name: 'Child Development' })).toBeVisible()
  })
})
