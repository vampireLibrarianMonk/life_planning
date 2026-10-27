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

# --- West standby: trigger an EXPLICIT deployment -------------------------
# East auto-deploys on this push, but the us-west-2 standby does NOT: App
# Runner's auto-deploy fires on a direct push to the watched repo, and the
# west image arrives via *cross-region ECR replication* (no push event). So
# without this step the standby silently lags the primary by a deploy (caught
# in the 2026-10-27 failover drill — see PHASE2_FAILOVER.md). This triggers the
# west service to pull the freshly-replicated :latest. Best-effort: a missing
# standby or a brief replication lag must not fail the primary deploy.
if [[ -n "${SERVICE_ARN_WEST:-}" ]]; then
  echo "[west] triggering standby deployment (us-west-2)…"
  if aws apprunner start-deployment \
       --service-arn "$SERVICE_ARN_WEST" --region us-west-2 \
       --query OperationId --output text 2>/dev/null; then
    echo "[west] deployment started. (If it no-ops, ECR replication may still"
    echo "       be in flight — re-run start-deployment in a minute.)"
  else
    echo "[west] WARN: could not start west deployment (replication lag or"
    echo "       service unavailable). Re-run:"
    echo "       aws apprunner start-deployment --service-arn \"\$SERVICE_ARN_WEST\" --region us-west-2"
  fi
fi

echo "       watch: ./deploy/monitor.sh watch"
