import { test, expect } from '@playwright/test'
import { loginAsAdmin, openFirstProfile } from './helpers.js'

/**
 * Child Development screen-capture walkthrough.
 *
 * Walks the CD section end-to-end and captures a screenshot at every step
 * into test-results/cd-walkthrough/ — dashboard, age-group cards, and the
 * 24mo detail view (legend, tri-state marks, domains, CDC items).
 *
 * Read-only: no data is created or mutated.
 */

const SHOT_DIR = 'test-results/cd-walkthrough'

async function shot(page, name) {
  await page.screenshot({ path: `${SHOT_DIR}/${name}.png`, fullPage: true })
}

test.describe('Child Development walkthrough (screen capture)', () => {
  test('captures the CD section end-to-end', async ({ page }) => {
    await loginAsAdmin(page)
    await openFirstProfile(page)
    await shot(page, '01-profile-dashboard')

    // Open the Child Development section (dashboard card: Early Growth Markers).
    await page.getByRole('button', { name: /Early Growth Markers/ }).click()
    await expect(page.getByRole('heading', { name: 'Child Development' })).toBeVisible()
    await shot(page, '02-cd-age-group-cards')

    // The 30mo group must appear in the catalog (CDC crosswalk addition).
    await expect(page.getByText('~30 Months (2.5 years)')).toBeVisible()

    // Open the 24mo age group (active on this profile).
    await page.getByRole('button', { name: /~24 Months/ }).click()
    await expect(page.getByRole('heading', { name: /~24 Months/ })).toBeVisible()
    await shot(page, '03-cd-24mo-detail-top')

    // Legend renders as bullets with the three marks.
    await expect(page.getByText('How to mark:')).toBeVisible()
    for (const mark of ['not yet', 'emerging', 'doing']) {
      await expect(page.locator('.cd-legend-list li', { hasText: mark }).first()).toBeVisible()
    }

    // The owner-requested CDC 24mo item is present.
    await expect(
      page.getByText('Notices when others are hurt or upset', { exact: false }),
    ).toBeVisible()

    // Scroll to the bottom of the checklist and capture the full sheet.
    await page.locator('.cd-notes').scrollIntoViewIfNeeded()
    await shot(page, '04-cd-24mo-detail-full')

    // Back to the age-group cards.
    await page.getByRole('button', { name: /All age groups/ }).click()
    await expect(page.getByRole('heading', { name: 'Child Development' })).toBeVisible()
    await shot(page, '05-cd-back-to-cards')
  })
})
