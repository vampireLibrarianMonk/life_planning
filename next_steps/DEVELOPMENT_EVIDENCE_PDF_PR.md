## TITLE

feat: resilient uploads and printable development evidence

## DESCRIPTION

## Summary

This PR completes the Gallery upload hardening work and adds the bounded
Development Goals evidence appendix to the browser-generated PDF.

## Upload resilience and privacy

- Gallery media can be linked to development objectives in either direction.
- Exact-content deduplication reuses only the same child's active canonical
  Gallery media, including direct/multipart video uploads.
- Multipart uploads use per-part checksums and the browser uses retry-friendly
  transfers.
- Deployment CORS guidance permits only the required app origins and upload
  headers.

## Printable evidence appendix

- Evidence is opt-in per objective and limited server-side to two photos and
  one video.
- A selected video renders only as a parent-selected photo cover card; PDFs do
  not contain playable video or original-size images.
- Preview images are private, resized derivatives served by the authenticated
  app; PDF evidence never receives an S3 or presigned URL.
- Cards include title, caption, date, an authenticated app deep link, and a
  visible omitted-item count. The print header warns that this is a private
  family record.

## Test and quality gates

- Full backend suite passes.
- Chromium creates a real PDF from synthetic media and verifies the two-photo
  layout, static video cover, caption, omitted count, no playable video, no S3
  URLs, and the size budget.
- Full pre-commit suite passes: Ruff, format, mypy, Bandit, secret scan,
  pip-audit, Hadolint, npm audit, and raw-HTML guard.

## Deployment note

Apply `deploy/uploads_cors.json` to the uploads bucket in both regions before
releasing the direct/multipart upload changes.
