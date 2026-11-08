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

// A >1MB PNG: a tiny valid header followed by padding, to prove uploads above
// the old 1MB JSON cap now pass (regression for the gallery 413 bug). The bytes
// after the header are ignored by the server (it stores whatever is sent).
const PNG_OVER_1MB = Buffer.concat([PNG_1PX, Buffer.alloc(1_300_000, 0)])

test.describe('Gallery', () => {
  test('upload, see, edit observation, filter, delete — synthetic image', async ({ page }) => {
    await loginAsAdmin(page)
    await openFirstProfile(page)

    await page.getByRole('button', { name: /Gallery/ }).first().click()
    await expect(page.getByRole('heading', { name: 'Gallery' })).toBeVisible()

    // Upload via the hidden file input behind "+ Add media". Use a >1MB file to
    // prove the body-size cap allows real photos (regression for the 413 bug).
    await page.setInputFiles('input[type=file]', {
      name: 'synthetic.png',
      mimeType: 'image/png',
      buffer: PNG_OVER_1MB,
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

  test('photo added on a Child Development objective also appears in the main Gallery', async ({ page }) => {
    await loginAsAdmin(page)
    await openFirstProfile(page)

    // Open Child Development → activate the ~12 Months group.
    await page.getByRole('button', { name: /Early Growth Markers/ }).click()
    await page.getByRole('button', { name: /~12 Months/ }).first().click()
    await expect(page.getByRole('heading', { name: '~12 Months' })).toBeVisible()
    // Activate if the group isn't seeded yet (wait for whichever state renders).
    const addGroup = page.getByRole('button', { name: 'Add this age group' })
    await Promise.race([
      addGroup.waitFor({ timeout: 8000 }).catch(() => {}),
      page.getByText('peekaboo or pat-a-cake', { exact: false }).waitFor({ timeout: 8000 }).catch(() => {}),
    ])
    if (await addGroup.isVisible().catch(() => false)) await addGroup.click()
    await expect(page.getByText('peekaboo or pat-a-cake', { exact: false })).toBeVisible({ timeout: 15000 })

    // Open the first objective's media panel and upload a synthetic photo.
    await page.getByTitle(/Accomplishment photos/).first().click()
    await page.setInputFiles('input[type=file]', {
      name: 'objective.png',
      mimeType: 'image/png',
      buffer: PNG_1PX,
    })
    // It renders in the objective's media panel (img alt falls back to filename).
    await expect(page.locator('img[alt="objective.png"]').first()).toBeVisible({ timeout: 10000 })

    // Now go to the main Gallery — the same photo must be there (one canonical gallery).
    await page.getByRole('button', { name: /All age groups/ }).click()
    await page.getByRole('button', { name: /Back to Dashboard/ }).click()
    await page.getByRole('button', { name: /Gallery/ }).first().click()
    await expect(page.getByRole('heading', { name: 'Gallery' })).toBeVisible()
    await expect(page.locator('.gallery-grid img')).toHaveCount(1)

    // Clean up: delete it from the Gallery, then remove the age group.
    page.once('dialog', (d) => d.accept())
    await page.getByTitle('Delete').first().click()
    await expect(page.locator('.gallery-grid img')).toHaveCount(0)
    await page.getByRole('button', { name: /Back to Dashboard/ }).click()
    await page.getByRole('button', { name: /Early Growth Markers/ }).click()
    await page.getByRole('button', { name: /~12 Months/ }).first().click()
    page.once('dialog', (d) => d.accept())
    await page.getByRole('button', { name: 'Remove this age group' }).click()
  })
})
