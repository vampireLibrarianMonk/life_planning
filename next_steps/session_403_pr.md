## TITLE

fix(auth): 30-day sessions + clear session-expired toast (fixes upload 403s)

## DESCRIPTION

# Root cause of the upload 403s: the 2-hour session lifetime

## Diagnosis (evidence, not guesswork)

- The entire upload pipeline was verified working server-side: buffered
  small upload (201), a real-sized 30KB photo (201), and the full
  direct-to-S3 22MB video flow (initiate 201 -> presigned PUT 200 ->
  finalize 200).
- The app logs showed ZERO gallery requests from the owner in 48h — the 403
  requests never appeared, and WAF logging (enabled during diagnosis) showed
  the owner's later attempts were ALLOWED through.
- The decisive reproduction: a 2.5-hour-old session cookie gets
  **401 "Invalid credentials"** from /api/auth/me.

**Root cause: `ACCESS_TOKEN_EXPIRE_MINUTES = 120`.** Sessions expired after
2 hours — mid-use. Every write (gallery and development-goal photo/video
uploads share the same endpoints) then failed with a 403/401 and no obvious
cause.

## Fixes

1. **auth.py** — session lifetime 2h -> **30 days**. A family app used in
   short bursts should not expire sessions mid-use.
2. **api.js** — the fetch interceptor now also dispatches `api-unauthorized`
   on 401 (excluding /api/auth/*), so an expired session reads as "sign in
   again" instead of a mystery per-endpoint error.
3. **ForbiddenToast.jsx** — listens for `api-unauthorized` and shows
   "Your session has expired — please sign in again."

## Verification

- Full backend suite: 148 passing; ruff clean; frontend builds clean.
- WAF logging was enabled during diagnosis (aws-waf-logs-life-planning) and
  stays on: any future blocked request names its rule.

## After merge

Deploy (build_push.sh), then **log out and log back in once** (the old
2-hour cookie is still in the browser), and uploads will work — and keep
working for 30 days per login.
