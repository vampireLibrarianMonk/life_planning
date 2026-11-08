import { test, expect } from '@playwright/test'
import { loginAsAdmin, openFirstProfile } from './helpers.js'

/**
 * Gallery (Pass 2) end-to-end: open the Gallery peer section, upload a synthetic
 * image (never a real child photo), see it appear, edit its observation, filter,
 * and delete it. Read-only is covered in readonly_ui.spec.js.
 */

// A 1x1 transparent PNG — synthetic test media only.
const PNG_1PX = Buffer.from(
  'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg==',
  'base64',
)

test.describe('Gallery', () => {
  test('upload, see, edit observation, filter, delete — synthetic image', async ({ page }) => {
    await loginAsAdmin(page)
    await openFirstProfile(page)

    await page.getByRole('button', { name: /Gallery/ }).first().click()
    await expect(page.getByRole('heading', { name: 'Gallery' })).toBeVisible()

    // Upload via the hidden file input behind "+ Add media".
    await page.setInputFiles('input[type=file]', {
      name: 'synthetic.png',
      mimeType: 'image/png',
      buffer: PNG_1PX,
    })

    // The tile appears with an <img>.
    const img = page.locator('.gallery-grid img').first()
    await expect(img).toBeVisible()

    // Edit the observation.
    await page.getByTitle('Edit observation').first().click()
    await page.locator('textarea').first().fill('First steps in the yard')
    await page.getByRole('button', { name: 'Save' }).click()
    await expect(page.getByText('First steps in the yard')).toBeVisible()

    // Photos filter still shows it; Videos filter hides it.
    await page.getByRole('button', { name: 'Videos' }).click()
    await expect(page.locator('.gallery-grid img')).toHaveCount(0)
    await page.getByRole('button', { name: 'Photos' }).click()
    await expect(page.locator('.gallery-grid img')).toHaveCount(1)

    // Delete (auto-accept the confirm dialog) and confirm it's gone.
    page.once('dialog', (d) => d.accept())
    await page.getByTitle('Delete').first().click()
    await expect(page.locator('.gallery-grid img')).toHaveCount(0)
  })
})
