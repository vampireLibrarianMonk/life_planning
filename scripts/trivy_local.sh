#!/usr/bin/env bash
# trivy_local.sh — run the SAME image-scan gate CI runs, locally.
#
# Usage:  scripts/trivy_local.sh [--skip-build]
#
# Builds life-planning:local (unless --skip-build) and scans it with the exact
# flags the CI image-scan job uses (HIGH,CRITICAL / ignore-unfixed /
# .trivyignore / exit-code 1). Requires: docker + a trivy binary on PATH
# (or at .venv/bin/trivy — install: see the comment below).
#
# Trivy single-binary install (no sudo):
#   curl -fsSL -o /tmp/trivy.tar.gz \
#     "https://github.com/aquasecurity/trivy/releases/download/v<VER>/trivy_<VER>_Linux-64bit.tar.gz"
#   tar -xzf /tmp/trivy.tar.gz -C /tmp trivy && mv /tmp/trivy ~/.local/bin/
set -euo pipefail
cd "$(dirname "$0")/.."

TRIVY="${TRIVY:-$(command -v trivy || echo .venv/bin/trivy)}"
IMAGE="life-planning:local"

if [[ "${1:-}" != "--skip-build" ]]; then
  echo "[build] docker build -t $IMAGE ."
  docker build -t "$IMAGE" .
fi

echo "[scan] trivy image --severity HIGH,CRITICAL --ignore-unfixed --ignorefile .trivyignore"
exec "$TRIVY" image \
  --exit-code 1 \
  --severity HIGH,CRITICAL \
  --ignore-unfixed \
  --ignorefile .trivyignore \
  "$IMAGE"
