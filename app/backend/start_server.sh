#!/usr/bin/env bash
# Launcher for the Life Plan Tracker backend.
# Starts uvicorn fully detached so it survives the parent shell exiting.
set -euo pipefail

BACKEND_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_UVICORN="$BACKEND_DIR/../../.venv/bin/uvicorn"
LOG_FILE="/tmp/life_plan_server.log"

cd "$BACKEND_DIR"

# Kill any existing instance
pkill -f "uvicorn main:app" 2>/dev/null || true
sleep 1

setsid "$VENV_UVICORN" main:app --host 0.0.0.0 --port 8000 \
  > "$LOG_FILE" 2>&1 < /dev/null &

echo "Server starting (log: $LOG_FILE)"
