#!/usr/bin/env bash
# Audit only the SHIPPED frontend deps (--omit=dev). A real HIGH+ advisory
# fails the commit; a transient npm-registry outage (5xx/timeout/DNS) is treated
# as a skip-with-warning so connectivity blips don't block commits.
set -u
cd "$(dirname "$0")/../app/frontend" || exit 1

out=$(npm audit --omit=dev --audit-level=high 2>&1)
rc=$?
if [ "$rc" -eq 0 ]; then
  exit 0
fi

if printf '%s' "$out" | grep -qiE 'audit endpoint returned an error|ETIMEDOUT|ENOTFOUND|ECONNRESET|network|503|Service Unavailable|EAI_AGAIN'; then
  echo "WARNING: npm audit skipped — registry unreachable (transient). Re-run before release."
  exit 0
fi

printf '%s\n' "$out"
exit "$rc"
