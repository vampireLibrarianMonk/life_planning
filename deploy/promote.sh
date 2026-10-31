#!/usr/bin/env bash
#
# promote.sh — deploy an already-pushed ECR image tag to both App Runner
# services by its immutable DIGEST (explicit, auditable promote). Pairs with
# build_push.sh --push-only. Usage: ./deploy/promote.sh <tag>
set -euo pipefail
cd "$(dirname "$0")/.."
set -a; . ./.arn-env; set +a

TAG="${1:?usage: promote.sh <image-tag>}"
REGION="${AWS_REGION:-us-east-1}"
REPO="${ECR_REPO_URI:?}"
REPO_NAME="${REPO##*/}"
REGISTRY="${REPO%%/*}"

DIGEST="$(aws ecr describe-images --repository-name "$REPO_NAME" --region "$REGION" \
  --image-ids imageTag="$TAG" --query 'imageDetails[0].imageDigest' --output text)"
echo "[promote] tag=$TAG digest=$DIGEST"

current_image_config() {
  aws apprunner describe-service --service-arn "$1" --region "$2" \
    --query 'Service.SourceConfiguration.ImageRepository.ImageConfiguration' --output json
}
promote() {
  local svc="$1" reg="$2" repo_host image_id
  repo_host="${REGISTRY/us-east-1/$reg}"
  image_id="${repo_host}/${REPO_NAME}@${DIGEST}"
  echo "[promote] $reg -> $image_id"
  aws apprunner update-service --service-arn "$svc" --region "$reg" \
    --source-configuration "{\"ImageRepository\":{\"ImageIdentifier\":\"$image_id\",\"ImageRepositoryType\":\"ECR\",\"ImageConfiguration\":$(current_image_config "$svc" "$reg")},\"AutoDeploymentsEnabled\":false}" \
    --query 'Service.Status' --output text
}
promote "$SERVICE_ARN" us-east-1
if [[ -n "${SERVICE_ARN_WEST:-}" ]]; then sleep 30; promote "$SERVICE_ARN_WEST" us-west-2; fi
echo "[done] promoted $TAG. watch: ./deploy/monitor.sh watch"
