## TITLE

docs(release): record 0.7.1 and cross-region backup status

## DESCRIPTION

## Release records

- Bumps the canonical `VERSION` ledger from `0.7.0` to `0.7.1` for the merged
  multipart Gallery upload resiliency and security/test fixes.
- Adds `CHANGELOG.md` with the release behavior, verification, immutable
  deployed digest, and controlled 40 MiB production upload evidence.

## Backup status

During the release audit, East Litestream was confirmed current and protected
by versioning plus seven-day Object Lock. West DB replication exposed an
operational defect: the S3 CRR role lacked the two Object Lock source-read
permissions AWS requires. Those least-privilege permissions were repaired live
on 2026-11-23.

The documentation deliberately does **not** mark West DR current yet: older DB
objects failed replication and the new object queue still requires confirmation
of `COMPLETED` status plus a controlled S3 Batch Replication backfill.

## Verification

- Documentation pre-commit gate passed (format, conflict, secret, dependency,
  and policy checks applicable to these files).
- Live S3 checks confirmed East versioning, seven-day GOVERNANCE Object Lock,
  enabled CRR rule, and current Litestream activity.
