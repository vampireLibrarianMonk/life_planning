#!/usr/bin/env bash
# Automated desktop + mobile evaluation of the Life Plan Tracker UI.
#
# Boots an ISOLATED backend (throwaway SQLite DB, local mode, free port),
# seeds one profile, builds the frontend, runs tests/device_eval.spec.js in
# every Playwright project (desktop + phones + 768px boundary), plus the
# read-only-account checks (tests/readonly_ui.spec.js), then tears
# everything down. Never touches the dev database or any deployed system.
#
# Usage:   scripts/eval_ui.sh [extra playwright args]
#   e.g.   scripts/eval_ui.sh --project=mobile-small
#          LP_SKIP_BUILD=1 scripts/eval_ui.sh      # reuse existing dist/
#
# Output:  app/frontend/eval-results/   (screenshots + summary-<project>.json)
#          app/frontend/playwright-report/ (HTML report)
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
FRONTEND="$ROOT/app/frontend"
BACKEND="$ROOT/app/backend"
PY="$ROOT/.venv-test/bin/python"
[ -x "$PY" ] || PY="$ROOT/.venv/bin/python"
[ -x "$PY" ] || { echo "No venv found (.venv-test or .venv)"; exit 2; }

PORT="${LP_EVAL_PORT:-$("$PY" -c 'import socket;s=socket.socket();s.bind(("127.0.0.1",0));print(s.getsockname()[1])')}"
WORK="$(mktemp -d)"
SERVER_PID=""

cleanup() {
  [ -n "$SERVER_PID" ] && kill "$SERVER_PID" 2>/dev/null || true
  rm -rf "$WORK"
}
trap cleanup EXIT

if [ -z "${LP_SKIP_BUILD:-}" ]; then
  echo "[eval] building frontend…"
  (cd "$FRONTEND" && npm run build --silent)
fi

echo "[eval] starting isolated backend on :$PORT"
(
  cd "$BACKEND"
  DEPLOY_MODE=local \
  SECRET_KEY="eval-only-secret-eval-only-secret-eval-only" \
  DATABASE_URL="sqlite:///$WORK/eval.db" \
  exec "$PY" -m uvicorn main:app --host 127.0.0.1 --port "$PORT" >"$WORK/server.log" 2>&1
) &
SERVER_PID=$!

for _ in $(seq 1 60); do
  curl -fs "http://127.0.0.1:$PORT/api/alive" >/dev/null 2>&1 && break
  kill -0 "$SERVER_PID" 2>/dev/null || { echo "[eval] server died:"; tail -20 "$WORK/server.log"; exit 1; }
  sleep 0.5
done
curl -fs "http://127.0.0.1:$PORT/api/alive" >/dev/null || { echo "[eval] server never became ready"; tail -20 "$WORK/server.log"; exit 1; }

echo "[eval] logging in once + seeding a test profile"
# The app throttles logins (10 / 5 min), so log in ONCE here and hand the
# session cookie to the specs instead of every project/worker logging in.
LP_SESSION_COOKIE="$("$PY" - "$PORT" <<'PY'
import json, sys, urllib.request
base = f"http://127.0.0.1:{sys.argv[1]}"
def call(path, data, cookie=None):
    h = {"Content-Type": "application/json", "Origin": base}
    if cookie: h["Cookie"] = cookie
    req = urllib.request.Request(base + path, json.dumps(data).encode(), h)
    return urllib.request.urlopen(req)
r = call("/api/auth/login", {"username": "admin", "password": "changeme"})
cookie = "; ".join(c.split(";")[0] for c in r.headers.get_all("Set-Cookie"))
call("/api/profiles/", {"name": "Test Child", "date_of_birth": "2015-06-01"}, cookie)
# A throwaway read-only (grandparent) account for tests/readonly_ui.spec.js.
call("/api/auth/register", {"username": "eval-readonly", "password": "Eval-readonly-pass-12345!", "display_name": "Eval RO", "role": "readonly"}, cookie)
print(cookie)
PY
)"
export LP_SESSION_COOKIE
export LP_RO_USER=eval-readonly LP_RO_PASS='Eval-readonly-pass-12345!'

rm -rf "$FRONTEND/eval-results"
cd "$FRONTEND"
set +e
LP_BASE_URL="http://127.0.0.1:$PORT" npx playwright test tests/device_eval.spec.js tests/readonly_ui.spec.js "$@"
RC=$?
set -e

echo
echo "[eval] screenshots + JSON summaries: $FRONTEND/eval-results/"
exit $RC
