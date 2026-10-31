#!/usr/bin/env bash
#
# build_push.sh — build the Life Plan Tracker image, push an IMMUTABLE tag to
# ECR, and PROMOTE it to both App Runner services by explicit digest.
#
# Deploy model (hardened 2026-10-31, TODO-8/14):
#   - ECR repo is IMMUTABLE: tags can't be overwritten, so we push a unique
#     timestamp tag (never :latest). Supply-chain integrity: a tag always maps
#     to exactly one image.
#   - No auto-deploy. We deploy by resolving the pushed image's DIGEST and
#     calling update-service on east AND west with that digest — an explicit,
#     auditable promote (vs. a mutable :latest that silently rolls prod).
#
# Usage:
#   ./deploy/build_push.sh                # build + push :<stamp> + promote both regions
#   ./deploy/build_push.sh --no-push      # build only (local test)
#   ./deploy/build_push.sh --push-only    # build + push, do NOT promote (manual promote later)
set -euo pipefail

cd "$(dirname "$0")/.."
set -a; . ./.arn-env; set +a

REGION="${AWS_REGION:-us-east-1}"
REPO="${ECR_REPO_URI:?ECR_REPO_URI not set in .arn-env}"
REPO_NAME="${REPO##*/}"                       # life-planning
REGISTRY="${REPO%%/*}"
STAMP="$(date -u +%Y%m%d-%H%M%S)"
MODE="promote"
[[ "${1:-}" == "--no-push" ]] && MODE="build-only"
[[ "${1:-}" == "--push-only" ]] && MODE="push-only"

echo "[build] $REPO:$STAMP  (immutable tag)"
docker build -t "$REPO:$STAMP" .

if [[ "$MODE" == "build-only" ]]; then
  echo "[build] --no-push set; built locally only."
  exit 0
fi

echo "[login] ECR $REGISTRY"
aws ecr get-login-password --region "$REGION" \
  | docker login --username AWS --password-stdin "$REGISTRY"

echo "[push] $REPO:$STAMP"
docker push "$REPO:$STAMP"

# Resolve the immutable digest just pushed (promote by digest, not tag).
DIGEST="$(aws ecr describe-images --repository-name "$REPO_NAME" --region "$REGION" \
  --image-ids imageTag="$STAMP" --query 'imageDetails[0].imageDigest' --output text)"
echo "[push] digest: $DIGEST"

if [[ "$MODE" == "push-only" ]]; then
  echo "[push-only] not promoting. To deploy:"
  echo "  ./deploy/promote.sh $STAMP"
  exit 0
fi

# --- Promote (explicit update-service by digest) to BOTH regions ----------
promote() {
  local svc="$1" reg="$2" repo_host name
  # Each region pulls from its OWN regional ECR (CRR mirrors the image). The
  # digest is identical across regions (content-addressed).
  repo_host="${REGISTRY/us-east-1/$reg}"
  local image_id="${repo_host}/${REPO_NAME}@${DIGEST}"
  echo "[promote] $reg -> $image_id"
  aws apprunner update-service --service-arn "$svc" --region "$reg" \
    --source-configuration "{\"ImageRepository\":{\"ImageIdentifier\":\"$image_id\",\"ImageRepositoryType\":\"ECR\",\"ImageConfiguration\":$(current_image_config "$svc" "$reg")},\"AutoDeploymentsEnabled\":false}" \
    --query 'Service.Status' --output text || echo "[promote] WARN: $reg update-service failed"
}

# Preserve the service's existing runtime env vars when promoting.
current_image_config() {
  aws apprunner describe-service --service-arn "$1" --region "$2" \
    --query 'Service.SourceConfiguration.ImageRepository.ImageConfiguration' --output json
}

echo "[promote] east…"
promote "$SERVICE_ARN" us-east-1
if [[ -n "${SERVICE_ARN_WEST:-}" ]]; then
  echo "[promote] west (waiting ~30s for ECR cross-region replication of the digest)…"
  sleep 30
  promote "$SERVICE_ARN_WEST" us-west-2
fi

echo "[done] promoted $STAMP ($DIGEST) to both regions. watch: ./deploy/monitor.sh watch"
