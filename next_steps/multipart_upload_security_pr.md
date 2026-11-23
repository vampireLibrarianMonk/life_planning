## TITLE

fix(uploads): make large video transfers resilient and clear CI security gates

## DESCRIPTION

## Summary

Large gallery videos now use S3 multipart upload instead of one long browser
PUT. The server creates and retains the multipart upload ID, returns only
short-lived signed URLs for 8 MiB parts, and finalizes only after it verifies
every expected part and the completed object's exact size. The browser uploads
each part with XHR, captures the S3 ETag, and retries transient failures.

This avoids the Safari/DuckDuckGo large-fetch failure mode while preserving the
existing small-file upload path.

## Security and integrity

- Multipart upload IDs stay server-side; clients cannot choose a bucket/key or
  finalize an arbitrary multipart upload.
- Finalization requires the complete ordered part set and rejects missing,
  malformed, or wrong-sized objects.
- Deleting media aborts any in-progress multipart upload; S3 also expires
  abandoned multipart uploads after seven days.
- The runtime Docker image now applies all available Debian updates during its
  build, clearing the fixed krb5 High CVEs detected by the image scanner.
- The CSRF test no longer reloads SQLAlchemy models mid-suite, which had split
  the mapper registry and caused unrelated CI tests to fail.

## Verification

Ran the same required checks as GitHub Actions locally:

- `pre-commit run --all-files --show-diff-on-failure` — passed (including
  mypy, Bandit, pip-audit, Hadolint, npm audit, secret detection, and SPA XSS
  sink detection).
- Backend Python 3.12 suite — 147 passed.
- `npm ci && npm run build` — passed.
- `docker build` plus the configured Trivy High/Critical scan — passed with
  zero findings.

## Deployment notes

No new client configuration or bucket policy relaxation is required. Existing
S3 CORS exposes `ETag`, which multipart completion needs. Deploy the merged
branch to both App Runner regions, then validate a real phone video upload in
Safari and DuckDuckGo.
