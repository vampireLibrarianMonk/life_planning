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

The repair was verified after this record was started: a new DB segment reached
`COMPLETED`/`REPLICA`, and Batch Replication job
`f865f310-da1b-4ad8-bebf-12498cb278ce` backfilled all **458/458** failed DB
objects with zero task failures. The independent daily snapshot remains open
for point-in-time recovery, because Litestream is replication rather than a
separate backup generation.

## Verification

- Documentation pre-commit gate passed (format, conflict, secret, dependency,
  and policy checks applicable to these files).
- Live S3 checks confirmed East versioning, seven-day GOVERNANCE Object Lock,
  enabled CRR rule, and current Litestream activity.
