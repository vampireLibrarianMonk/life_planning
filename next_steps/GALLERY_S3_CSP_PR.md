# fix(uploads): allow Gallery multipart PUTs through CSP

## Root cause

A live, authenticated Gallery upload of a disposable 40 MiB `video/mp4` file
reproduced the owner-visible failure. Browser tracing showed the first
presigned S3 `PUT` was cancelled with failure text `csp`, before it reached
S3. The application CSP allowed S3 only for `img-src` and `media-src`; it
omitted `connect-src`, so its `default-src 'self'` rule blocked the
XMLHttpRequest used for multipart part uploads. Safari and DuckDuckGo surface
that browser-side block as a generic network/load failure.

## Change

Add a `connect-src` directive for only the three S3 endpoint patterns already
allowed to render Gallery images and videos:

- `https://*.s3.amazonaws.com`
- `https://*.s3.us-east-1.amazonaws.com`
- `https://*.s3.us-west-2.amazonaws.com`

No permissive `*` or blanket `https:` source was added. Presigned URL signing,
bucket CORS, authentication, and the existing media-display policy are
unchanged.

## Verification

- New middleware regression test checks the precise `connect-src` allow-list
  and rejects `connect-src *`.
- Targeted CSP/CSRF middleware tests: 8 passed.
- Frontend production build passed.
- Full pre-commit gate passed, including mypy, Bandit, pip-audit, Hadolint,
  npm audit, and secret detection.
- Production Docker image build and HIGH/CRITICAL Trivy scan passed.

## Follow-up validation

After merge and App Runner deployment, repeat the authenticated Gallery UI
test with a disposable 40 MiB video and delete the test record/object. This
is the first browser-level test of the precise path that failed; prior direct
S3/API probes could not reveal the app CSP block.

## Separate existing test-suite issue

The complete backend suite currently stalls in the pre-existing archive
round-trip test while draining a `StreamingResponse` (`test_delete_profile.py`,
line 108). The targeted upload/security tests pass; the archive test needs a
separate repair and is outside this narrowly scoped browser-CSP fix.
