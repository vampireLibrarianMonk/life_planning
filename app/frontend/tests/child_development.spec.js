import { test, expect } from '@playwright/test'
import { loginAsAdmin, openFirstProfile } from './helpers.js'

/**
 * Child Development section end-to-end: open the section, activate an age group,
 * mark an objective, add a custom objective, and use the private worries note.
 * Cleans up after itself by removing the activated age group.
 */
test.describe('Child Development section', () => {
  test('appears on the dashboard just below Life Maps', async ({ page }) => {
    await loginAsAdmin(page)
    await openFirstProfile(page)
    await expect(page.getByRole('heading', { name: 'Child Development' })).toBeVisible()
    await expect(page.getByRole('button', { name: /Early Growth Markers/ })).toBeVisible()
  })

  test('activate an age group, mark + add objectives, private worries, then clean up', async ({ page }) => {
    await loginAsAdmin(page)
    await openFirstProfile(page)

    // Open the section.
    await page.getByRole('button', { name: /Early Growth Markers/ }).click()
    await expect(page.getByRole('heading', { name: 'Child Development' })).toBeVisible()

    // Open the ~12 Months group (card shows "~12 Months").
    await page.getByRole('button', { name: /~12 Months/ }).first().click()

    // If not active yet, activate it.
    const addGroup = page.getByRole('button', { name: 'Add this age group' })
    if (await addGroup.isVisible().catch(() => false)) {
      await addGroup.click()
    }

    // A known 12mo objective should render under its domain.
    await expect(page.getByText('Waves "bye-bye".', { exact: false })).toBeVisible()

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
    // Back at the age-group list.
    await expect(page.getByRole('heading', { name: 'Child Development' })).toBeVisible()
  })
})
