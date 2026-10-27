#!/usr/bin/env bash
#
# failover_control.sh — SAFE, operator-gated regional failover / fail-back.
#
# WHY THIS EXISTS
# ---------------
# The Route 53 record is a PRIMARY/SECONDARY failover pair with health checks on
# BOTH sides, so fail-back to east is AUTOMATIC the moment east's health check
# recovers. Combined with one-directional CRR (east->west ONLY; the west DB
# bucket has no replication back to east), that is a SILENT DATA-LOSS bug:
#
#   east dies -> traffic -> west -> family writes land ONLY in the west DB bucket
#   east recovers -> Route 53 auto-fails-back -> east restores from its OWN
#   (frozen) bucket -> every write made on west during the outage is lost.
#
# Making CRR bidirectional is NOT a safe fix: two Litestream writers replicating
# into each other's bucket corrupts the SQLite generation chain (the exact
# active/active hazard the single-writer design forbids).
#
# The correct fix is a GATED fail-back: when east comes back, DO NOT let it
# auto-promote until an operator has reconciled west's data into east. This
# script provides the safe primitives. It is READ-ONLY by default; mutating
# actions require an explicit subcommand AND a typed confirmation.
#
# USAGE
#   ./deploy/failover_control.sh status            # show DNS + health + which region is live
#   ./deploy/failover_control.sh hold-east         # pause east auto-fail-back (detach primary health check)
#   ./deploy/failover_control.sh reconcile-to-east # copy the CURRENT live (west) DB generation east->... (prints steps; gated)
#   ./deploy/failover_control.sh release-east       # re-attach primary health check (resume normal failover)
#
# All resource IDs come from .arn-env.
set -euo pipefail
cd "$(dirname "$0")/.."
set -a; . ./.arn-env; set +a

ZID="${HOSTED_ZONE_ID:-Z0101762W5VWFT32BT2B}"
PRIMARY_HC="5a717b94-b385-4f16-9ce4-edf9ab1e49f1"
EAST_DB="${DB_REPLICA_BUCKET:?}"
WEST_DB="${DB_REPLICA_BUCKET_WEST:?}"

_confirm() {
  read -r -p "Type EXACTLY '$1' to proceed: " ans
  [[ "$ans" == "$1" ]] || { echo "aborted."; exit 1; }
}

cmd="${1:-status}"
case "$cmd" in
  status)
    echo "=== live region (custom domain /api/health) ==="
    curl -s -m10 https://life-planning.my-deployment.com/api/health \
      | python3 -c "import sys,json;print('  region:',json.load(sys.stdin)['config']['region'])" || true
    echo "=== primary health check status ==="
    aws route53 get-health-check-status --health-check-id "$PRIMARY_HC" \
      --query "HealthCheckObservations[].StatusReport.Status" --output text 2>/dev/null | head -1 || true
    echo "=== east DB bucket last-modified vs west (newest Litestream object) ==="
    aws s3 ls "s3://$EAST_DB/life_plan.db/" --recursive 2>/dev/null | sort | tail -1 | awk '{print "  east:",$1,$2}' || echo "  (east: none)"
    aws s3 ls "s3://$WEST_DB/life_plan.db/" --recursive 2>/dev/null | sort | tail -1 | awk '{print "  west:",$1,$2}' || echo "  (west: none)"
    ;;

  hold-east)
    # Prevent auto-fail-back: disassociate the primary health check so Route 53
    # keeps serving SECONDARY (west) until an operator explicitly releases it.
    echo "This DETACHES the primary health check so east will NOT auto-reclaim traffic."
    _confirm "HOLD-EAST"
    echo "Fetch current PRIMARY record, re-put it WITHOUT a health check id…"
    echo ">>> Manual step (printed, not executed): edit the PRIMARY record-set to drop HealthCheckId,"
    echo "    or temporarily set its Failover weight so west stays authoritative. See runbook in"
    echo "    deploy/PHASE2_FAILOVER.md §Fail-back. (Left manual on purpose — DNS is high-blast-radius.)"
    ;;

  reconcile-to-east)
    # Copy the authoritative (currently-live) west DB generation into east BEFORE
    # releasing auto-fail-back, so east restores from west's data, not its stale copy.
    echo "This will overwrite the EAST DB bucket's life_plan.db with the WEST (live) copy."
    echo "Do this ONLY while west is the authoritative writer and east is held (hold-east)."
    _confirm "RECONCILE-TO-EAST"
    echo "Syncing the WHOLE Litestream generation tree s3://$WEST_DB/life_plan.db/ -> s3://$EAST_DB/life_plan.db/ …"
    echo "(Litestream stores generations/snapshots/WAL under this prefix; a single-object copy is NOT enough.)"
    aws s3 sync "s3://$WEST_DB/life_plan.db/" "s3://$EAST_DB/life_plan.db/" --sse aws:kms --delete
    echo "Done. On east's next boot, litestream restore picks the newest generation (west's)."
    echo "VERIFY east serves the reconciled data (sentinel check) BEFORE release-east."
    ;;

  release-east)
    echo "This re-attaches the primary health check so normal east-primary failover resumes."
    echo "Only run AFTER reconcile-to-east (or if no writes happened on west)."
    _confirm "RELEASE-EAST"
    echo ">>> Manual step (printed): re-put the PRIMARY record-set WITH HealthCheckId=$PRIMARY_HC."
    echo "    (Left manual on purpose — confirm east is serving the reconciled data first.)"
    ;;

  *)
    echo "unknown command: $cmd"; exit 2;;
esac
