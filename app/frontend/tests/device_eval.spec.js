import { test, expect } from '@playwright/test'
import AxeBuilder from '@axe-core/playwright'
import { ADMIN_USER, ADMIN_PASS, openFirstProfile } from './helpers.js'
import fs from 'node:fs'
import path from 'node:path'

/**
 * Automated evaluation of the app in desktop AND mobile modes.
 *
 * Runs once per Playwright project (desktop / mobile-pixel / mobile-iphone /
 * mobile-small / tablet-768). For every key view it checks:
 *
 *   1. Device-mode detection matches the viewport (breakpoint 767px).
 *   2. No horizontal page overflow (nothing pokes past the viewport).
 *   3. Touch targets are big enough on touch devices (>= 24px WCAG 2.2 AA
 *      minimum is GATING; the 44px best-practice target is REPORTED).
 *   4. No uncaught page errors or console errors.
 *   5. Mode-specific layout is actually applied (e.g. pillars scroll
 *      horizontally on mobile, wrap in a grid on desktop).
 *   6. axe-core serious/critical violations (same gate as a11y.spec.js).
 *
 * A screenshot per view/project and a JSON summary are written to
 * `eval-results/` (git-ignored) for human review.
 *
 * Read-only: no data is created or mutated.
 */

const BREAKPOINT = 767
const MIN_TARGET_GATE = 24 // WCAG 2.2 SC 2.5.8 (AA) minimum
const MIN_TARGET_GOAL = 44 // Apple HIG / WCAG 2.5.5 (AAA) recommendation
const OUT_DIR = path.resolve('eval-results')

const findings = [] // per-test report rows, flushed in afterAll

// The backend throttles logins (10 / 5 min per IP+user), so never log in per
// test. scripts/eval_ui.sh logs in once and passes the cookie via
// LP_SESSION_COOKIE ("lp_auth=<jwt>"); if it's absent (running the spec
// directly), log in once per project through the API.
let sessionCookies = []

test.beforeAll(async ({ browser, baseURL }) => {
  const raw = process.env.LP_SESSION_COOKIE
  if (raw) {
    const host = new URL(baseURL).hostname
    sessionCookies = raw.split(/;\s*/).filter(Boolean).map((kv) => {
      const i = kv.indexOf('=')
      return { name: kv.slice(0, i), value: kv.slice(i + 1), domain: host, path: '/' }
    })
    return
  }
  const ctx = await browser.newContext({ baseURL })
  const res = await ctx.request.post('/api/auth/login', {
    data: { username: ADMIN_USER, password: ADMIN_PASS },
  })
  expect(res.ok(), `API login failed: ${res.status()}`).toBeTruthy()
  sessionCookies = await ctx.cookies()
  await ctx.close()
})

/** Start an authenticated session on the Dashboard without a UI login. */
async function openDashboard(page) {
  await page.context().addCookies(sessionCookies)
  await page.goto('/')
  await expect(page.getByRole('heading', { name: 'Profiles' })).toBeVisible()
}

function record(row) {
  findings.push(row)
}

test.afterAll(async ({}, testInfo) => {
  if (!findings.length) return
  fs.mkdirSync(OUT_DIR, { recursive: true })
  fs.writeFileSync(
    path.join(OUT_DIR, `summary-${testInfo.project.name}.json`),
    JSON.stringify(findings, null, 2),
  )
})

/** Collect console errors + uncaught exceptions for the lifetime of a page. */
function watchErrors(page) {
  const errors = []
  page.on('pageerror', (e) => errors.push(`pageerror: ${e.message}`))
  page.on('console', (m) => {
    if (m.type() !== 'error') return
    const t = m.text()
    // The unauthenticated session probe on the login page legitimately 401s.
    if (/401|Unauthorized|Failed to load resource.*(401|403)/i.test(t)) return
    errors.push(`console.error: ${t}`)
  })
  return errors
}

/** Elements (within the page) that extend beyond the viewport's right edge. */
async function horizontalOverflow(page) {
  return page.evaluate(() => {
    const vw = document.documentElement.clientWidth
    const doc = document.documentElement
    const pageOverflow = doc.scrollWidth - vw
    const offenders = []
    for (const el of document.body.querySelectorAll('*')) {
      const r = el.getBoundingClientRect()
      if (r.width === 0 || r.height === 0) continue
      if (r.right <= vw + 1) continue
      // Content inside an intentionally scrollable container is fine.
      let p = el.parentElement
      let clipped = false
      while (p && p !== document.body) {
        const ox = getComputedStyle(p).overflowX
        if (ox === 'auto' || ox === 'scroll' || ox === 'hidden') { clipped = true; break }
        p = p.parentElement
      }
      if (clipped) continue
      offenders.push({
        tag: el.tagName.toLowerCase(),
        cls: (el.className && el.className.toString().slice(0, 40)) || '',
        text: (el.textContent || '').trim().slice(0, 30),
        right: Math.round(r.right),
      })
      if (offenders.length >= 8) break
    }
    return { vw, pageOverflow, offenders }
  })
}

/**
 * Interactive elements that are laid out (not display:none, not in a closed
 * <details>) yet have zero width or height: content squeezed out of existence.
 * smallTargets() skips zero-size elements, so without this a collapsed layout
 * passes the target-size check by having nothing left to measure.
 */
async function collapsedControls(page) {
  return page.evaluate(() => {
    const sel = 'button, a[href], input:not([type=hidden]), select, textarea, [role=button], summary'
    const out = []
    for (const el of document.querySelectorAll(sel)) {
      if (el.checkVisibility && !el.checkVisibility()) continue
      const r = el.getBoundingClientRect()
      if (r.width < 2 || r.height < 2) {
        out.push({ tag: el.tagName.toLowerCase(), label: (el.textContent || '').trim().slice(0, 30), w: Math.round(r.width), h: Math.round(r.height) })
      }
    }
    return out
  })
}

/** Interactive elements smaller than the given size (visible ones only). */
async function smallTargets(page, min) {
  return page.evaluate((min) => {
    const sel = 'button, a[href], input:not([type=hidden]), select, textarea, [role=button], summary'
    const out = []
    for (const el of document.querySelectorAll(sel)) {
      const r = el.getBoundingClientRect()
      const cs = getComputedStyle(el)
      if (r.width === 0 || r.height === 0 || cs.visibility === 'hidden' || cs.display === 'none') continue
      // Inline text links inside a sentence are exempt from target-size rules.
      if (el.tagName === 'A' && cs.display === 'inline') continue
      if (r.width < min || r.height < min) {
        out.push({
          tag: el.tagName.toLowerCase(),
          label: (el.getAttribute('aria-label') || el.textContent || el.getAttribute('placeholder') || '').trim().slice(0, 30),
          w: Math.round(r.width),
          h: Math.round(r.height),
        })
      }
    }
    return out
  }, min)
}

/** Wait until the DOM stops changing (network never idles: the failover banner polls /api/health). */
async function settle(page, quietMs = 400, maxMs = 8000) {
  await page.evaluate(([quiet, max]) => new Promise((resolve) => {
    let t = setTimeout(done, quiet)
    const cap = setTimeout(done, max)
    const mo = new MutationObserver(() => { clearTimeout(t); t = setTimeout(done, quiet) })
    mo.observe(document.body, { subtree: true, childList: true, attributes: true, characterData: true })
    function done() { mo.disconnect(); clearTimeout(t); clearTimeout(cap); resolve() }
  }), [quietMs, maxMs])
}

async function checkView(page, testInfo, view, errors) {
  const project = testInfo.project.name
  const isTouch = await page.evaluate(() => matchMedia('(pointer: coarse)').matches || navigator.maxTouchPoints > 0)

  // 1. Detection agrees with the viewport and is exposed on <html>.
  const dev = await page.evaluate(() => ({
    attr: document.documentElement.getAttribute('data-device'),
    state: window.__lpDevice,
    width: document.documentElement.clientWidth,
  }))
  const expected = dev.width <= BREAKPOINT ? 'mobile' : 'desktop'
  expect(dev.attr, `${view}: <html data-device> should be "${expected}" at ${dev.width}px`).toBe(expected)
  expect(dev.state?.mode).toBe(expected)

  // 2. No horizontal overflow.
  const ov = await horizontalOverflow(page)
  expect(
    ov.pageOverflow,
    `${view}: page scrolls horizontally by ${ov.pageOverflow}px at ${ov.vw}px wide. Offenders: ${JSON.stringify(ov.offenders)}`,
  ).toBeLessThanOrEqual(1)

  // 2b. Nothing interactive squeezed down to (almost) nothing.
  const collapsed = await collapsedControls(page)
  expect(
    collapsed,
    `${view}: ${collapsed.length} control(s) collapsed to ~0px: ${JSON.stringify(collapsed.slice(0, 6))}`,
  ).toEqual([])

  // 3. Touch-target sizing (touch devices only).
  let belowGoal = []
  if (isTouch) {
    const tooSmall = await smallTargets(page, MIN_TARGET_GATE)
    belowGoal = await smallTargets(page, MIN_TARGET_GOAL)
    expect(
      tooSmall,
      `${view}: ${tooSmall.length} touch target(s) under ${MIN_TARGET_GATE}px: ${JSON.stringify(tooSmall.slice(0, 6))}`,
    ).toEqual([])
  }

  // 4. No runtime errors.
  expect(errors, `${view}: runtime errors`).toEqual([])

  // 6. axe serious/critical.
  const axe = await new AxeBuilder({ page })
    .withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa'])
    .analyze()
  const serious = axe.violations.filter((v) => v.impact === 'serious' || v.impact === 'critical')
  expect(
    serious.map((v) => `${v.id} (${v.nodes.length}) e.g. ${v.nodes[0]?.target?.join(' ')} :: ${(v.nodes[0]?.failureSummary || '').split('\n').slice(1, 3).join(' ').slice(0, 160)}`),
    `${view}: axe serious/critical`,
  ).toEqual([])

  // Evidence for humans.
  fs.mkdirSync(OUT_DIR, { recursive: true })
  await page.screenshot({
    path: path.join(OUT_DIR, `${project}-${view.replace(/\W+/g, '_')}.png`),
    fullPage: false,
  })

  record({
    project,
    view,
    mode: dev.attr,
    viewport: dev.width,
    touch: isTouch,
    horizontalOverflowPx: ov.pageOverflow,
    targetsBelow44: belowGoal.length,
    axeViolations: axe.violations.length,
  })
}

test.describe('Device-mode evaluation', () => {
  test('Login view', async ({ page }, testInfo) => {
    const errors = watchErrors(page)
    await page.goto('/')
    await expect(page.getByRole('heading', { name: 'Life Plan Tracker' })).toBeVisible()
    await checkView(page, testInfo, 'login', errors)
  })

  test('Dashboard view', async ({ page }, testInfo) => {
    const errors = watchErrors(page)
    await openDashboard(page)
    await checkView(page, testInfo, 'dashboard', errors)
  })

  test('Profile view uses the layout for its mode', async ({ page }, testInfo) => {
    const errors = watchErrors(page)
    await openDashboard(page)
    await openFirstProfile(page)

    // 5. Mode-specific layout: mobile = one horizontally scrolling row,
    //    desktop = multi-column wrapping grid.
    const grid = page.locator('.pillar-grid-desktop').first()
    await expect(grid).toBeVisible()
    const mode = await page.evaluate(() => document.documentElement.getAttribute('data-device'))
    const layout = await grid.evaluate((el) => {
      const cs = getComputedStyle(el)
      return { display: cs.display, overflowX: cs.overflowX }
    })
    if (mode === 'mobile') {
      expect(layout.display, 'mobile pillars should be a flex row').toBe('flex')
      expect(layout.overflowX, 'mobile pillars should scroll horizontally').toBe('auto')

      // Regression guard: the open roadmap row's badge list must use the row's
      // width, not be squeezed into a narrow column beside the title.
      const squeeze = await page.evaluate(() => {
        const d = document.querySelector('.roadmap-phase[open]')
        const body = d && d.querySelector(':scope > div')
        if (!d || !body) return null
        return { row: d.getBoundingClientRect().width, body: body.getBoundingClientRect().width }
      })
      expect(squeeze, 'an open roadmap phase should exist').not.toBeNull()
      expect(
        squeeze.body / squeeze.row,
        `roadmap badges squeezed to ${Math.round(squeeze.body)}px of ${Math.round(squeeze.row)}px row`,
      ).toBeGreaterThan(0.6)
    } else {
      expect(layout.display, 'desktop pillars should be a grid').toBe('grid')
    }

    await checkView(page, testInfo, 'profile', errors)
  })

  test('Programs view', async ({ page }, testInfo) => {
    const errors = watchErrors(page)
    await openDashboard(page)
    await openFirstProfile(page)
    await page.getByRole('button', { name: /Programs/ }).first().click()
    await expect(page.getByRole('button', { name: /Back to Dashboard/ })).toBeVisible()
    await checkView(page, testInfo, 'programs', errors)
  })

  test('Bounty Board view', async ({ page }, testInfo) => {
    test.setTimeout(90_000)
    const errors = watchErrors(page)
    await openDashboard(page)
    await openFirstProfile(page)
    await page.getByRole('button', { name: /Bounty Board/ }).first().click()
    await expect(page.getByRole('button', { name: /Back to Dashboard/ })).toBeVisible()
    // The bounty list loads after the shell renders. Measuring before it
    // arrives checks an almost-empty page and passes for the wrong reason.
    await expect(page.getByText(/Adopt-a-Space|Broken Window Repair|Be the Change/).first()).toBeVisible()
    await expect.poll(() => page.locator('button').count(), { message: 'bounty list should render' }).toBeGreaterThan(200)
    await checkView(page, testInfo, 'bounty-board', errors)
  })

  // Every section reachable from a profile. Each is opened read-only and run
  // through the same checks as the main views (overflow, collapsed controls,
  // touch targets, errors, axe).
  const SECTIONS = [
    ['life-chart', /Life Chart Card/],
    ['belonging', /Breadth of Belonging/],
    ['early-growth', /Early Growth Markers/],
    ['pillar-spiritual', /^✝️Spiritual/],
    ['pillar-civic', /Civic & Institutional/],
    ['wishlist', /^🎁Wishlist/],
    ['career', /^💼Career/],
    ['lesson-plans', /^📖Lesson Plans/],
    ['discernment-health', /^🫀Health/],
    ['discernment-calling', /^📣Calling/],
  ]
  for (const [name, label] of SECTIONS) {
    test(`Section: ${name}`, async ({ page }, testInfo) => {
      test.setTimeout(60_000)
      const errors = watchErrors(page)
      await openDashboard(page)
      await openFirstProfile(page)
      await page.locator('button', { hasText: label }).first().click()
      await expect(page.getByRole('button', { name: /Back to|All age groups/ }).first()).toBeVisible()
      await settle(page)
      await checkView(page, testInfo, name, errors)
    })
  }

  test('Section: early-growth age group (detail level)', async ({ page }, testInfo) => {
    const errors = watchErrors(page)
    await openDashboard(page)
    await openFirstProfile(page)
    await page.locator('button', { hasText: /Early Growth Markers/ }).first().click()
    await expect(page.getByRole('heading', { name: 'Child Development' })).toBeVisible()
    await page.locator('.pillar-grid-desktop button').first().click()
    await expect(page.getByRole('button', { name: /All age groups/ })).toBeVisible()
    await settle(page)
    await checkView(page, testInfo, 'early-growth-group', errors)
  })

  test('Dashboard no longer shows the duplicate Child Development disclaimer', async ({ page }) => {
    await openDashboard(page)
    await openFirstProfile(page)
    await expect(page.getByRole('heading', { name: 'Child Development' })).toBeVisible()
    await expect(page.getByText('A gentle guide, not a test', { exact: false })).toHaveCount(0)
  })

  test('Detection reacts live to a viewport resize', async ({ page }) => {
    await page.goto('/')
    await expect(page.getByRole('heading', { name: 'Life Plan Tracker' })).toBeVisible()
    const mode = () => page.evaluate(() => document.documentElement.getAttribute('data-device'))
    await page.setViewportSize({ width: 1280, height: 800 })
    await expect.poll(mode).toBe('desktop')
    await page.setViewportSize({ width: BREAKPOINT, height: 800 })
    await expect.poll(mode).toBe('mobile')
    await page.setViewportSize({ width: BREAKPOINT + 1, height: 800 })
    await expect.poll(mode).toBe('desktop')
    await page.setViewportSize({ width: 375, height: 667 })
    await expect.poll(mode).toBe('mobile')
  })
})
