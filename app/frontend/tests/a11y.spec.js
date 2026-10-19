import { test, expect } from '@playwright/test'
import AxeBuilder from '@axe-core/playwright'
import { loginAsAdmin, openFirstProfile } from './helpers.js'

/**
 * Accessibility scans using axe-core (WCAG 2.0/2.1 A & AA).
 *
 * GATING by default: the baseline was triaged and fixed, so these tests now FAIL
 * on any serious/critical violation. Set LP_A11Y_STRICT=0 to downgrade to
 * report-only (log violations without failing) while investigating a regression.
 */

const FAIL_ON_SERIOUS = process.env.LP_A11Y_STRICT !== '0'

function summarize(label, results) {
  const violations = results.violations || []
  const bySeverity = violations.reduce((acc, v) => {
    acc[v.impact || 'unknown'] = (acc[v.impact || 'unknown'] || 0) + 1
    return acc
  }, {})
  // eslint-disable-next-line no-console
  console.log(`\n[a11y] ${label}: ${violations.length} violation rule(s) — ${JSON.stringify(bySeverity)}`)
  for (const v of violations) {
    // eslint-disable-next-line no-console
    console.log(`  • [${v.impact}] ${v.id}: ${v.help} (${v.nodes.length} node(s))`)
    console.log(`    ${v.helpUrl}`)
  }
  if (FAIL_ON_SERIOUS) {
    const serious = violations.filter(v => v.impact === 'serious' || v.impact === 'critical')
    expect(serious, `${label} has serious/critical a11y violations`).toEqual([])
  }
}

async function scan(page, label) {
  const results = await new AxeBuilder({ page })
    .withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa'])
    .analyze()
  summarize(label, results)
}

test.describe('Accessibility scans', () => {
  test('Login page', async ({ page }) => {
    await page.goto('/')
    await expect(page.getByRole('heading', { name: 'Life Plan Tracker' })).toBeVisible()
    await scan(page, 'Login')
  })

  test('Dashboard', async ({ page }) => {
    await loginAsAdmin(page)
    await scan(page, 'Dashboard')
  })

  test('Profile view', async ({ page }) => {
    await loginAsAdmin(page)
    await openFirstProfile(page)
    await scan(page, 'Profile')
  })

  test('Programs view', async ({ page }) => {
    await loginAsAdmin(page)
    await openFirstProfile(page)
    await page.getByRole('button', { name: /Programs/ }).first().click()
    await expect(page.getByRole('button', { name: /Back to Dashboard/ })).toBeVisible()
    await scan(page, 'Programs')
  })

  test('Bounty Board (Economy) view', async ({ page }) => {
    // The bounty board can render hundreds of bounty instances; axe analysis on a
    // very large DOM is slow, so give this scan a larger budget.
    test.setTimeout(90_000)
    await loginAsAdmin(page)
    await openFirstProfile(page)
    await page.getByRole('button', { name: /Bounty Board/ }).first().click()
    await expect(page.getByRole('button', { name: /Back to Dashboard/ })).toBeVisible()
    await scan(page, 'Bounty Board')
  })
})
