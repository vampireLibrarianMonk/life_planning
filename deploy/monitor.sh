#!/usr/bin/env bash
#
# monitor.sh — one-stop deployment status + health + diagnostics for the
# Life Plan Tracker on AWS App Runner.
#
# Usage:
#   ./deploy/monitor.sh status     # App Runner service state + last operation
#   ./deploy/monitor.sh health     # curl the public /api/health (mode/region)
#   ./deploy/monitor.sh logs       # tail recent CloudWatch logs (build+app)
#   ./deploy/monitor.sh dns        # resolve the domain + show cert/domain state
#   ./deploy/monitor.sh watch      # poll service state until RUNNING/failed
#   ./deploy/monitor.sh smoke      # run the Playwright walkthrough vs the live URL
#   ./deploy/monitor.sh all        # status + health + dns in one shot
#
# Config via env (overrides the defaults below):
#   AWS_REGION, SERVICE_NAME, DOMAIN, SERVICE_ARN
#
set -uo pipefail

AWS_REGION="${AWS_REGION:-us-east-1}"
SERVICE_NAME="${SERVICE_NAME:-life-planning}"
DOMAIN="${DOMAIN:-life-planning.my-deployment.com}"
URL="https://${DOMAIN}"

c_green=$'\e[32m'; c_red=$'\e[31m'; c_yellow=$'\e[33m'; c_blue=$'\e[36m'; c_off=$'\e[0m'
say()  { printf '%s[monitor]%s %s\n' "$c_blue" "$c_off" "$*"; }
ok()   { printf '%s  ✓%s %s\n' "$c_green" "$c_off" "$*"; }
warn() { printf '%s  !%s %s\n' "$c_yellow" "$c_off" "$*"; }
err()  { printf '%s  ✗%s %s\n' "$c_red" "$c_off" "$*"; }

# Resolve the App Runner service ARN from its name (cached in SERVICE_ARN).
resolve_arn() {
  if [[ -n "${SERVICE_ARN:-}" ]]; then echo "$SERVICE_ARN"; return; fi
  aws apprunner list-services --region "$AWS_REGION" \
    --query "ServiceSummaryList[?ServiceName=='${SERVICE_NAME}'].ServiceArn | [0]" \
    --output text 2>/dev/null
}

cmd_status() {
  local arn; arn="$(resolve_arn)"
  if [[ -z "$arn" || "$arn" == "None" ]]; then
    err "No App Runner service named '${SERVICE_NAME}' in ${AWS_REGION} yet."
    return 1
  fi
  say "Service: ${SERVICE_NAME}  (${AWS_REGION})"
  aws apprunner describe-service --service-arn "$arn" --region "$AWS_REGION" \
    --query "Service.{Status:Status,URL:ServiceUrl,Updated:UpdatedAt}" --output table
  say "Recent operations:"
  aws apprunner list-operations --service-arn "$arn" --region "$AWS_REGION" \
    --max-results 5 \
    --query "OperationSummaryList[].{Type:Type,Status:Status,Started:StartedAt,Ended:EndedAt}" \
    --output table
}

cmd_health() {
  say "GET ${URL}/api/health"
  local body code
  body="$(curl -s -m 10 -w '\n%{http_code}' "${URL}/api/health" 2>/dev/null)"
  code="$(printf '%s' "$body" | tail -n1)"
  body="$(printf '%s' "$body" | sed '$d')"
  if [[ "$code" == "200" ]]; then
    ok "HTTP 200"
    printf '%s\n' "$body" | (command -v jq >/dev/null && jq . || cat)
  else
    err "HTTP ${code:-no-response} — service may be deploying, failing over, or down."
    [[ -n "$body" ]] && printf '%s\n' "$body"
  fi
}

cmd_logs() {
  local arn svc_id grp
  arn="$(resolve_arn)"
  svc_id="$(printf '%s' "$arn" | awk -F/ '{print $NF}')"
  say "Recent CloudWatch logs for ${SERVICE_NAME} (${svc_id})"
  for suffix in application service; do
    grp="/aws/apprunner/${SERVICE_NAME}/${svc_id}/${suffix}"
    echo "--- log group: ${grp} ---"
    local stream
    stream="$(aws logs describe-log-streams --log-group-name "$grp" --region "$AWS_REGION" \
      --order-by LastEventTime --descending --max-items 1 \
      --query "logStreams[0].logStreamName" --output text 2>/dev/null)"
    if [[ -z "$stream" || "$stream" == "None" ]]; then
      warn "no streams yet in ${suffix}"
      continue
    fi
    aws logs get-log-events --log-group-name "$grp" --log-stream-name "$stream" \
      --region "$AWS_REGION" --limit 40 --query "events[].message" --output text 2>/dev/null \
      | sed 's/^/    /'
  done
}

cmd_dns() {
  say "DNS resolution for ${DOMAIN}"
  if command -v dig >/dev/null; then
    dig +short "$DOMAIN" || true
  else
    nslookup "$DOMAIN" 2>/dev/null | sed -n '/Name:/,$p' || true
  fi
  local arn; arn="$(resolve_arn)"
  if [[ -n "$arn" && "$arn" != "None" ]]; then
    say "Custom domain / certificate status:"
    aws apprunner describe-custom-domains --service-arn "$arn" --region "$AWS_REGION" \
      --query "CustomDomains[].{Domain:DomainName,Status:Status,CertStatus:CertificateValidationRecords[0].Status}" \
      --output table 2>/dev/null || warn "no custom domain attached yet"
  fi
  say "TLS check:"
  curl -sS -m 10 -o /dev/null -w "  HTTP %{http_code}  (TLS %{ssl_verify_result}=0 means OK)\n" "$URL" 2>&1 || \
    err "TLS/connection failed (cert may still be issuing)"
}

cmd_watch() {
  local arn; arn="$(resolve_arn)"
  if [[ -z "$arn" || "$arn" == "None" ]]; then err "service not found"; return 1; fi
  say "Watching ${SERVICE_NAME} until it settles (Ctrl-C to stop)…"
  while true; do
    local st
    st="$(aws apprunner describe-service --service-arn "$arn" --region "$AWS_REGION" \
      --query "Service.Status" --output text 2>/dev/null)"
    printf '%s  %s\n' "$(date +%H:%M:%S)" "$st"
    case "$st" in
      RUNNING)                 ok "service is RUNNING"; cmd_health; break ;;
      CREATE_FAILED|PAUSED|DELETE_FAILED) err "terminal state: $st — check 'logs'"; break ;;
    esac
    sleep 15
  done
}

cmd_smoke() {
  say "Live smoke test (Playwright walkthrough) against ${URL}"
  ( cd "$(dirname "$0")/../app/frontend" && LP_BASE_URL="$URL" npx playwright test tests/walkthrough.spec.js )
}

case "${1:-all}" in
  status) cmd_status ;;
  health) cmd_health ;;
  logs)   cmd_logs ;;
  dns)    cmd_dns ;;
  watch)  cmd_watch ;;
  smoke)  cmd_smoke ;;
  all)    cmd_status; echo; cmd_health; echo; cmd_dns ;;
  *) echo "usage: $0 {status|health|logs|dns|watch|smoke|all}"; exit 2 ;;
esac
