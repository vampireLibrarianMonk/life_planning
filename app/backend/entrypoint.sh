#!/bin/sh
# Container entrypoint: restore the SQLite DB from S3 (if a replica exists),
# then run the app under Litestream so every change streams back to S3.
#
# This makes the DB survive App Runner redeploys (the container filesystem is
# ephemeral). In local mode (no DB_REPLICA_BUCKET) it falls back to running
# the app directly, so the same image works locally.
set -e

DB_PATH=/app/backend/life_plan.db

if [ -n "$DB_REPLICA_BUCKET" ]; then
  echo "[entrypoint] DB replica bucket set: $DB_REPLICA_BUCKET — restoring if present"
  # -if-replica-exists: no error on first-ever boot (empty bucket).
  litestream restore -if-replica-exists -config /app/backend/litestream.yml "$DB_PATH" || true

  echo "[entrypoint] starting app under litestream replication"
  exec litestream replicate -config /app/backend/litestream.yml \
    -exec "uvicorn main:app --host 0.0.0.0 --port 8000"
else
  echo "[entrypoint] no DB_REPLICA_BUCKET — running app directly (local mode)"
  exec uvicorn main:app --host 0.0.0.0 --port 8000
fi
