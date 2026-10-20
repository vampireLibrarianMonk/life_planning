#!/usr/bin/env bash
#
# build_push.sh — build the Life Plan Tracker image and push it to ECR.
#
# App Runner is configured to auto-deploy when a new image lands on the
# :latest tag, so running this script triggers a rolling redeploy. Old images
# are pruned automatically by the ECR lifecycle policy (keep newest 5).
#
# Usage:
#   ./deploy/build_push.sh                # build + push :latest and a timestamp tag
#   ./deploy/build_push.sh --no-push      # build only (local test)
#
set -euo pipefail

cd "$(dirname "$0")/.."                      # repo root
set -a; . ./.arn-env; set +a                 # ECR_REPO_URI, AWS region, etc.

REGION="${AWS_REGION:-us-east-1}"
REPO="${ECR_REPO_URI:?ECR_REPO_URI not set in .arn-env}"
REGISTRY="${REPO%%/*}"                        # 8097...dkr.ecr.us-east-1.amazonaws.com
STAMP="$(date -u +%Y%m%d-%H%M%S)"
PUSH=1
[[ "${1:-}" == "--no-push" ]] && PUSH=0

echo "[build] $REPO:latest  (+ :$STAMP)"
docker build -t "$REPO:latest" -t "$REPO:$STAMP" .

if [[ "$PUSH" -eq 0 ]]; then
  echo "[build] --no-push set; built locally only."
  exit 0
fi

echo "[login] ECR $REGISTRY"
aws ecr get-login-password --region "$REGION" \
  | docker login --username AWS --password-stdin "$REGISTRY"

echo "[push] $REPO:latest and :$STAMP"
docker push "$REPO:latest"
docker push "$REPO:$STAMP"

echo "[done] pushed. App Runner auto-deploy (if enabled) will roll this out."
echo "       watch: ./deploy/monitor.sh watch"
