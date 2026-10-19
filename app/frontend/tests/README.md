# UI Walkthrough & Accessibility Testing

Automated browser testing for the Life Plan Tracker frontend using
[Playwright](https://playwright.dev/) and [axe-core](https://github.com/dequelabs/axe-core)
(`@axe-core/playwright`).

## What it covers

- **`tests/walkthrough.spec.js`** — a read-only end-to-end walk through the app: login,
  dashboard, profile view, opening a development pillar, the Programs view (asserts the
  newly added **Just War Ethics** and **City of God** programs render), and the Bounty
  Board (asserts the new civic-sense commons bounties render).
- **`tests/a11y.spec.js`** — axe-core WCAG 2.0/2.1 A & AA scans of the Login, Dashboard,
  Profile, Programs, and Bounty Board views.

## Prerequisites

1. Backend + built frontend running on `http://localhost:8000`:
   ```bash
   cd app/frontend && npm run build
   cd ../backend && ./start_server.sh      # or: uvicorn main:app --host 0.0.0.0 --port 8000
   ```
2. Browser binary installed (one-time):
   ```bash
   cd app/frontend && npx playwright install chromium
   ```

## Running

```bash
cd app/frontend
npm run test:e2e     # walkthrough only
npm run test:a11y    # accessibility scans only
npm test             # everything
```

Point at a different host with `LP_BASE_URL`, and override credentials with
`LP_ADMIN_USER` / `LP_ADMIN_PASS`.

## Accessibility mode: gating vs. report-only

The a11y scans **gate by default** — they fail the run on any serious/critical
violation. The initial baseline was triaged and fixed (see below), so the suite is
green under gating.

To temporarily downgrade to **report-only** (log violations without failing, e.g. while
investigating a regression):

```bash
LP_A11Y_STRICT=0 npm run test:a11y
```

## Baseline findings (triaged and fixed)

The first scan (axe-core 4.10, tags `wcag2a`/`wcag2aa`/`wcag21a`/`wcag21aa`) surfaced two
issue classes, both now resolved:

| Issue | Where | Root cause | Fix |
|-------|-------|-----------|-----|
| `color-contrast` (serious) | Dashboard, Profile, Programs, Bounty Board | Muted greys (`#888`/`#999`/`#aaa`/`#bbb`), a too-light green (`#2ecc71`), blue (`#4a90d9`), amber/orange (`#f5a623`/`#e67e22`) and tier identity colors (gold `#ffd700`, diamond `#b9f2ff`, etc.) used as **text** on white/light backgrounds below 4.5:1 | Darkened text tokens to AA-compliant equivalents (e.g. grey → `#595959`, green → `#15803d`, blue → `#2563b0`). Added `TIER_TEXT_COLORS` in `Economy.jsx` so tier **text** uses AA-safe colors while `TIER_COLORS` stays for swatches/borders. Darkened the blue/grey button backgrounds that carried white text. |
| `scrollable-region-focusable` (serious) | Bounty Board + scrollable panels | Scrollable `<div>`/`<pre>` regions had no keyboard focus path | Added `tabIndex={0}` + `role="region"` + `aria-label` to each scrollable region (Economy incidents/tier-list/log, Profile transcript/guide/sub-panel, `MiniMarkdown`). |

Result: **0 violations across all five scanned views.** Tier identity colors are preserved
for non-text UI (swatches, borders, progress bars) where contrast rules don't apply.

### If you add new UI
- Prefer the darkened text tokens over raw brand colors for any text on a light background.
- Any new scrollable container needs `tabIndex={0}` (+ `role="region"` + `aria-label`).
- Run `npm run test:a11y` before committing; it will fail if you reintroduce a serious violation.

## Artifacts

Playwright writes `playwright-report/` and `test-results/` (HTML report, traces,
screenshots on failure). Both are git-ignored.
