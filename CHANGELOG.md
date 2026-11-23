# Changelog

All notable released changes are recorded here. The canonical application
version remains the first line of [`VERSION`](VERSION).

## [0.7.1] - 2026-11-23

### Fixed

- Replaced the fragile one-request large Gallery video transfer with S3
  multipart uploads in AWS mode. The browser uploads 8 MiB signed parts via
  XHR, retries transient part failures, and submits the returned ETags.
- Kept S3 multipart upload IDs server-side. Finalization now rejects incomplete
  or unordered parts and mismatched object sizes; deleting pending media aborts
  its multipart session.
- Stopped the CSRF middleware test from reloading SQLAlchemy models mid-suite,
  which caused unrelated `BountyLog` mapper failures in CI.
- Applied all available Debian package updates during the production image
  build, clearing the fixed krb5 High findings from the image scan.

### Verified

- GitHub-equivalent local gates passed: 147 backend tests, complete pre-commit
  security gate, frontend production build, and Trivy High/Critical scan with
  zero findings.
- Deployed merge `9a3029d` to East and West App Runner using immutable image
  digest `sha256:d1d15bc…ec334`; both health endpoints and the authenticated
  six-test live walkthrough passed.
- Two controlled 40 MiB, five-part production uploads finalized successfully
  and their temporary gallery records were confirmed removed.

## [0.7.0] - 2026-11-09

- Added contacts/recipient directory, media share grants, contact verification,
  and the messaging foundation. See [`VERSION`](VERSION) for the complete
  historical ledger.
