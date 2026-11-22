# Upload Troubleshooting Handoff — for Codex

Date: 2026-11-22. State: image uploads FIXED and verified live; ONE issue
remains open: **~40MB phone videos fail in Safari with "Load failed"** after
the upload appears to complete. This document gives you the full context,
the changelog of what was fixed, and the ranked hypotheses + fix directions
for the remaining issue.

## 1. Upload architecture (as built)

Two-path system, chosen per file size in `app/frontend/src/services/api.js`
(`smartUploadGalleryMedia`):

- **Under 20MB** (`DIRECT_UPLOAD_THRESHOLD`): buffered multipart POST to
  `POST /api/profiles/{id}/gallery/` (routes/gallery.py). The app writes to
  S3 via storage.py. The security middleware in main.py caps bodies at
  **50MB for upload paths / 1MB for JSON** (Content-Length check).
- **20MB and over**: direct-to-S3. `POST .../gallery/uploads/initiate`
  reserves a pending row and returns a presigned PUT URL
  (`storage.py presigned_put_url`, TTL `config.PRESIGN_TTL_SECONDS`);
  the browser PUTs the bytes straight to S3 (CORS on the uploads bucket
  allows PUT/GET/HEAD from https://life-planning.my-deployment.com with
  Content-Type); then `POST .../uploads/{id}/finalize` verifies the object
  landed and flips status to ready. S3 single-PUT limit: 5GB.

Key code locations:
- `app/frontend/src/services/api.js` — smartUploadGalleryMedia,
  directUploadGalleryMedia (the fetch PUT), uploadGalleryMedia
- `app/backend/routes/gallery.py` — buffered upload, initiate, finalize
- `app/backend/storage.py` — S3Storage.presigned_put_url (signs ContentType)
- `app/backend/config.py` — PRESIGN_TTL_SECONDS
- `app/backend/main.py` — body-size middleware (50MB/1MB)
- Uploads bucket (east): `life-planning-uploads-1640485eadc0037f642bf3a8`

## 2. Changelog — the THREE 403 diseases found and fixed (2026-11-22)

All three surfaced as "upload failed 403" with identical symptoms. In
hindsight there were three distinct causes:

### Fix 1 — Session lifetime (PR #14, MERGED + DEPLOYED, digest fab412ff)
`ACCESS_TOKEN_EXPIRE_MINUTES` was 120 (2h). Sessions expired mid-use; every
write 403/401'd. Fixed: 30 days (auth.py). Also added a 401 interceptor
(api.js dispatches `api-unauthorized`) + a "session has expired" toast
(ForbiddenToast.jsx). VERIFIED LIVE: fresh token expires in 30.0 days.

### Fix 2 — WAF body-inspection rules (applied DIRECTLY to the WAF, LIVE)
The AWS Managed Common Rule Set's body rules were BLOCKing real photo
uploads (5 blocks logged from the owner's IP on POST /gallery/). Binary
JPEG bytes trip XSS/SQLi text patterns. Fixed: RuleActionOverrides on the
`AWSCommonRules` managed group now set `SizeRestrictions_BODY`,
`CrossSiteScripting_BODY`, `SQLi_BODY`, `GenericRFI_BODY` to COUNT mode
(logged, not blocked). All other rules stay BLOCK. VERIFIED LIVE: the
owner's actual 25MB jpg uploaded end-to-end through the exact browser flow
(CORS preflight 200 + Origin PUT 200 + finalize 200).
WAF ACL: `life-planning-waf` (REGIONAL, us-east-1, id 7923219c-...).

### Fix 3 — Presigned URL TTL (PR OPEN, NOT YET DEPLOYED)
`PRESIGN_TTL_SECONDS` was 900 (15 min). A 1GB video on ~3 Mbps takes ~45
min; the PUT URL expired mid-upload; S3 returned 403 "Request has expired"
(masked by CORS as a generic network error). Fix in the open PR: 900 -> 3600.
Branch: `fix/presign-ttl-large-uploads`. **MERGE + DEPLOY THIS FIRST** — it
is verified (148 tests) and removes the expiry failure mode for big files.

## 3. THE OPEN ISSUE: ~40MB phone video -> Safari "Load failed"

### Symptom (owner, 2026-11-22)
On iPhone Safari (private browsing, on WiFi): a ~40MB video "seems to
upload" then the UI shows **"Load failed"** — Safari's fetch TypeError
message (the Safari equivalent of Firefox's "NetworkError when attempting
to fetch resource"). The upload progress appears to run, then the fetch
rejects at the network level. Images now work on the same device.

### What "Load failed" tells us
It is NOT an HTTP status (those surface as "Upload transfer failed (HTTP
N)"). The fetch itself failed: either the connection broke, CORS masked an
S3 error response, or Safari aborted the request. The 40MB file takes the
DIRECT path (>= 20MB): initiate -> browser PUT to the S3 presigned URL ->
finalize. The failure is almost certainly on the **cross-origin S3 PUT**.

### Ranked hypotheses
1. **Safari + large fetch() body (STRONGEST).** Safari buffers large
   request bodies and has documented problems with fetch PUTs of large
   Blobs on iOS (memory pressure, especially private browsing). 25MB
   worked from desktop curl; 40MB from a PHONE is a different memory
   envelope. Fix direction: switch the PUT to **XMLHttpRequest** (streams
   better on Safari) or implement **S3 multipart upload** (chunk the file
   into 5-8MB parts, presign each part, PUT parts + complete). Multipart
   also fixes the TTL issue for huge files and enables resume.
2. **Content-Type signature mismatch.** storage.py signs the presigned URL
   WITH ContentType. If the phone's file.type (e.g. video/quicktime for
   .mov, or an empty type) differs from what Safari actually sends on the
   PUT, S3 returns SignatureDoesNotMatch (403) and Safari masks it as
   "Load failed". Fix direction: log/compare the initiate content_type vs
   the PUT; or presign WITHOUT ContentType and set the object content-type
   at finalize (copy-with-metadata) so a mismatch is impossible.
3. **WiFi/network interruption on a long PUT.** A 40MB PUT on congested
   WiFi can drop; fetch has no retry. Fix direction: retry with backoff on
   the PUT (idempotent — same presigned URL until TTL), or multipart with
   per-part retry.
4. **Presign TTL (ruled out for 40MB on WiFi — ~1-4 min upload — but merge
   the open PR anyway; it matters for 1GB+ files).**

### Diagnostic runbook (everything is already instrumented)
- **WAF logs** (CloudWatch `aws-waf-logs-life-planning`): any BLOCK/COUNT
  is logged with rule + IP within seconds. The body rules now COUNT, so a
  tripped rule shows as action COUNT (non-blocking) — check `labels`.
- **App logs** (CloudWatch
  `/aws/apprunner/life-planning/9be584e163a04d9fb3def96cb1519cb4/application`):
  uvicorn access lines show initiate/finalize statuses. If initiate is 201
  and finalize never arrives, the PUT died in the browser.
- **S3 server access logging is NOT enabled** on the uploads bucket —
  enabling it (or S3 Request Metrics) would show whether the PUT reached
  S3 at all and with what status. Worth doing.
- **Browser console on the phone** (Mac Safari > Develop > iPhone): the
  fetch error + any CORS message distinguishes hypothesis 1 vs 2.
- Repro file: the owner has a ~40MB phone video; desktop repro of the
  same flow with Safari (WebKit) via Playwright may reproduce it without
  the phone.

### Suggested fix order
1. Merge + deploy the open presign-TTL PR (removes hypothesis 4).
2. Add PUT retry-on-network-error with one re-initiate (cheap, helps 3).
3. Investigate 1 vs 2 with the diagnostics above; the durable fix for
   both is **S3 multipart upload** (5-8MB parts, presigned per part,
   per-part retry, complete-multipart at finalize) — it sidesteps Safari's
   large-body problems, the TTL, and single-connection drops all at once.
   The initiate/finalize API shape extends naturally (part URLs list).

## 4. Versions / state at handoff

- master: PR #14 merged (session fix); presign-TTL PR open
  (`fix/presign-ttl-large-uploads`).
- Deployed image (both regions): digest `fab412ff...` (20261122-175925).
- WAF: body rules in COUNT mode (live, applied 2026-11-22 ~15:38 ET).
- WAF logging: ON (`aws-waf-logs-life-planning`).
- Backend suite: 148 passing. Frontend builds clean.
- VERSION file: check `VERSION` at repo root for the app version ledger.
