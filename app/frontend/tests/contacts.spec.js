import { test, expect } from '@playwright/test'
import { loginAsAdmin, openFirstProfile } from './helpers.js'

/**
 * Contacts (v6 Pass 4) end-to-end: open the Contacts section, add a contact,
 * see it listed, remove it. Uses synthetic data only (no real PII).
 */
test.describe('Contacts', () => {
  test('add, see, remove a contact', async ({ page }) => {
    await loginAsAdmin(page)
    await openFirstProfile(page)

    await page.getByRole('button', { name: /Contacts/ }).first().click()
    await expect(page.getByRole('heading', { name: 'Contacts' })).toBeVisible()
    // The label-is-not-permission note must be shown.
    await expect(page.getByText(/does .*not.* give anyone access/i)).toBeVisible()

    await page.getByRole('button', { name: '+ Add contact' }).click()
    await page.getByPlaceholder(/Name \(e\.g\./).fill('Dr. Synthetic')
    await page.getByPlaceholder('name@example.com').fill('dr.synthetic@example.com')
    await page.getByRole('button', { name: 'Save' }).click()

    await expect(page.getByText('Dr. Synthetic')).toBeVisible()
    await expect(page.getByText('dr.synthetic@example.com')).toBeVisible()
    // Unverified by default (no auto-trust of a typed address).
    await expect(page.getByText(/unverified/)).toBeVisible()

    // Remove it.
    page.once('dialog', (d) => d.accept())
    await page.getByTitle('Remove from this child').first().click()
    await expect(page.getByText('Dr. Synthetic')).toHaveCount(0)
  })
})
