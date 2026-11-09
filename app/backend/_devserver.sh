#!/usr/bin/env bash
# Fully-detached local dev server launcher (survives the parent shell).
cd "$(dirname "$0")"
pkill -f "uvicorn main:app" 2>/dev/null || true
sleep 1
setsid ../../.venv/bin/uvicorn main:app --host 0.0.0.0 --port 8000 \
  </dev/null >/tmp/life_plan_server.log 2>&1 &
echo "started pid $!"
