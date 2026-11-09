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
    await page.getByPlaceholder('+1 555 555 0123').fill('+15555550199')

    // Role = Family -> the dependent "Relationship" dropdown appears.
    const roleSelect = page.locator('form select').first()
    await roleSelect.selectOption('family')
    await expect(page.getByText('Relationship', { exact: true })).toBeVisible()
    await page.locator('form select').nth(1).selectOption('mother')

    // Switch role to Pediatrician -> the Relationship dropdown disappears.
    await roleSelect.selectOption('pediatrician')
    await expect(page.getByText('Relationship', { exact: true })).toHaveCount(0)
    // Back to Family + pick a sub-type for the save.
    await roleSelect.selectOption('family')
    await page.locator('form select').nth(1).selectOption('grandmother')

    await page.getByRole('button', { name: 'Save' }).click()

    await expect(page.getByText('Dr. Synthetic')).toBeVisible()
    await expect(page.getByText('dr.synthetic@example.com')).toBeVisible()
    await expect(page.getByText('+15555550199')).toBeVisible()
    // Unverified by default (no auto-trust of a typed address).
    await expect(page.getByText(/unverified/).first()).toBeVisible()

    // Verify the email via the dev-code flow (console backend echoes the code).
    await page.getByRole('button', { name: 'Verify' }).first().click()
    const devLine = page.getByText(/your code is/i)
    await expect(devLine).toBeVisible()
    const codeText = await devLine.textContent()
    const code = (codeText.match(/\b(\d{6})\b/) || [])[1]
    expect(code, 'dev code present').toBeTruthy()
    await page.getByPlaceholder('6-digit code').fill(code)
    await page.getByRole('button', { name: 'Confirm' }).click()
    await expect(page.getByText(/· verified/).first()).toBeVisible()

    // Remove it.
    page.once('dialog', (d) => d.accept())
    await page.getByTitle('Remove from this child').first().click()
    await expect(page.getByText('Dr. Synthetic')).toHaveCount(0)
  })
})
