# Playwright Guide — Child Development Screen-Capture Walkthrough

How to run the automated screen-capture walkthrough of the Child Development
section and where the captures land.

## What it is

`app/frontend/tests/cd_walkthrough.spec.js` walks the Child Development
section end-to-end in a real browser and captures a **full-page screenshot
at every step**. It is read-only for your data: the only writes are
idempotent age-group seeds (36/48/60mo) so their checklists render.

## What it captures (screenshot inventory)

| File | Step |
|---|---|
| `01-profile-dashboard.png` | The profile dashboard after login |
| `02-cd-age-group-cards.png` | Child Development age-group cards (incl. the 30mo group) |
| `03-cd-24mo-detail-top.png` | The 24mo checklist: bulleted legend, tri-state marks, domains |
| `04-cd-24mo-detail-full.png` | The full 24mo sheet scrolled to the notes |
| `05-cd-back-to-cards.png` | Back on the age-group cards |
| `06-cd-36mo-commands-danger.png` | 36mo: 2-3 step instructions + family danger rules |
| `07-cd-48mo-commands-danger-stairs.png` | 48mo: delayed instructions + danger-rule WHY + stairs-DOWN alternating + ladder climbing |
| `08-cd-60mo-commands-danger-jumping.png` | 60mo: conditional instructions + danger rules applied + jumping jacks/scissor jumps |

## Prerequisites

1. Backend + built frontend running on `http://localhost:8000`:
   ```bash
   cd app/frontend && npm run build
   cd ../backend && ./start_server.sh
   ```
2. Browser binary (one-time):
   ```bash
   cd app/frontend && npx playwright install chromium
   ```
3. Login: the walkthrough logs in as admin (local defaults `admin`/`changeme`,
   overridable via `LP_ADMIN_USER` / `LP_ADMIN_PASS` env vars).

## Running

```bash
cd app/frontend && npx playwright test cd_walkthrough.spec.js
```

The run takes under a minute. Exit code 0 = every step captured and every
assertion passed.

## Where the captures land

`app/frontend/test-results/cd-walkthrough/` — one PNG per step (see the
inventory above). Open them directly, or view the whole set at once:

```bash
xdg-open app/frontend/test-results/cd-walkthrough/01-profile-dashboard.png
```

The folder is regenerated on every run (screenshots are overwritten, not
accumulated).

## Notes

- The walkthrough seeds the 36/48/60mo age groups via the API (idempotent)
  so their checklists render; it never changes marks or custom items.
- The 24mo assertions include the CDC item "Notices when others are hurt or
  upset" and the bulleted legend; the 36/48/60mo assertions include the
  instruction-following progression (2-3 step -> delayed -> conditional) and
  the danger-awareness progression (curb-stop -> names rules -> explains why
  -> applies without reminders), plus the alternating-legs stairs item.
- The full test suite (all specs) runs with `npx playwright test` from
  `app/frontend`; see `app/frontend/tests/README.md` for the complete
  testing guide.
