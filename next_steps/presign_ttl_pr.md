## TITLE

fix(uploads): presigned URL TTL 15min -> 1h (large videos were 403ing mid-upload)

## DESCRIPTION

# Boundary testing found the real large-upload bug: the presigned URL expired mid-upload

## Boundary test results (all against prod, faux files with real extensions)

| Test | Path | Result |
|---|---|---|
| 19MB .jpg | Buffered (just under the 20MB threshold) | 201 OK |
| 21MB .jpg | Direct-to-S3 (just over) | initiate 201 / PUT 200 / finalize 200 |
| 21MB .mp4 | Direct-to-S3 | all green |
| 100MB .mp4 | Direct-to-S3 | PUT 200 in 44s, finalize 200 |
| S3 bucket CORS | Browser path | Verified correct (PUT/GET/HEAD from the app origin, Content-Type allowed, ETag exposed) |

## Root cause of the misleading errors

`PRESIGN_TTL_SECONDS = 900` (15 minutes). A 1GB phone video on a ~3 Mbps
uplink takes ~45 minutes to upload — the presigned PUT URL **expired
mid-upload**, and S3 returned **403 "Request has expired"**. The frontend
surfaced it as *"Upload transfer failed (HTTP 403)"* — indistinguishable
from the session-expiry 403 fixed in the previous PR. That is exactly the
"errors that are not what they seem" the owner reported for larger photos
and videos.

## Fix

TTL default **900 -> 3600** (1 hour), still env-overridable via
`PRESIGN_TTL_SECONDS`. Covers a 1GB upload on a ~2.5 Mbps connection.
Presigned GET (display) URLs also live 1h now — harmless, they are
re-generated fresh on every fetch.

## Verification

- Full backend suite: 148 passing; ruff clean.
- All boundary test media cleaned from Robert's gallery (ids 13-16).

## After merge

Deploy (build_push.sh). No user action needed — the next large upload just
works.
