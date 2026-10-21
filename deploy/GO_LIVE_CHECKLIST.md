# Go-Live Checklist — Phase 1 (single region, us-east-1)

> ✅ **COMPLETED 2026-10-20.** The app is live at
> `https://life-planning.my-deployment.com`. This file is retained as a record
> of the go-live sequence. For the accurate **as-built** record (which differs
> from the original plan — ECR image build instead of GitHub source, plus
> Litestream, autoscaling pin, alerting, and the go-live fixes) see
> **`DEPLOYMENT_STEPS.md`**. Operate the live app with `./deploy/monitor.sh`.

Target: `https://life-planning.my-deployment.com`.
Monitor helper: `./deploy/monitor.sh {status|health|logs|dns|watch|smoke|all}`

> Note: the original plan below assumed an App Runner **GitHub-source** build.
> In practice the CLI/API only supports managed runtimes, so we built a
> **Dockerfile image → ECR** and App Runner deploys from ECR with auto-deploy
> on `:latest`. See `DEPLOYMENT_STEPS.md` for the real steps.

---

## 0. Pre-flight (do first, ~2 min)

- [ ] `git fetch && git status` — confirm in sync with `origin/master` (it is).
- [ ] Tonight's modular commits pushed to GitHub (App Runner builds from the repo).
- [ ] `aws sts get-caller-identity` — confirm account `809784555426`.
- [ ] `pre-commit run --all-files` green; `./.venv/bin/python -m pytest` green.

## 1. Secrets & keys (CLI, ~5 min)

- [ ] JWT secret created → record `JWT_SECRET_ARN`  (DEPLOYMENT_STEPS §1)
- [ ] KMS key + alias `alias/life-planning` created  (§2)
- [ ] Admin secret already exists ✓ `life-planning/admin-credentials`

## 2. Storage & IAM (CLI, ~5 min)

- [ ] S3 bucket `$UPLOADS_BUCKET` (random-suffix name in `.arn-env`): BPA on, versioning on,
      SSE-KMS default, TLS-only policy  (§3)
- [ ] App Runner instance role with scoped secrets/S3/KMS permissions  (§4)

## 3. App Runner service (Console, ~10 min + build)

- [ ] Create service → GitHub source → connect repo/branch  (§5)
      *(Console step — needs your click for the GitHub handshake.)*
- [ ] Dockerfile build, port `8000`, health path `/api/health`
- [ ] Instance role from step 2; env vars set (DEPLOY_MODE=aws, ARNs, bucket)
- [ ] Deploy, then **watch it build**:
      ```
      ./deploy/monitor.sh watch        # polls until RUNNING or failure
      ./deploy/monitor.sh logs         # if the build/boot fails, read why
      ```

## 4. Edge & DNS (~10 min + propagation)

- [ ] WAF regional web ACL created + associated to the service  (§6)
- [ ] Custom domain `life-planning.my-deployment.com` added in App Runner  (§7)
- [ ] Validation CNAMEs + domain record added to Route 53 zone
      `Z0101762W5VWFT32BT2B`
- [ ] Watch cert/domain go Active:
      ```
      ./deploy/monitor.sh dns          # resolution + cert/domain status + TLS
      ```

## 5. Verify live (~5 min)

- [ ] `./deploy/monitor.sh all`  → status RUNNING, health `mode: aws`, DNS OK
- [ ] `./deploy/monitor.sh smoke` → Playwright walkthrough against the live URL
- [ ] Manual eyeball: log in (password from Secrets Manager), upload an
      attachment (confirm it round-trips via S3 presigned URL), click a program.
      ```
      aws secretsmanager get-secret-value --secret-id life-planning/admin-credentials \
        --region us-east-1 --query SecretString --output text
      ```

## 6. Cleanup

- [ ] Delete orphan CNAME `_3cce7ec…app.housing-planner.com` in zone
      `Z02860032ZNCH6LLUL27W` (unrelated leftover).

---

## If something breaks — fast triage

| Symptom | Command | Likely cause |
|---------|---------|--------------|
| Service won't reach RUNNING | `monitor.sh logs` | Docker build error, or boot crash (missing env var / secret perms) |
| `health` returns 403/blocked | check WAF rules | `/api/health` not allow-listed above WAF rules |
| `health` 500 / "refusing to start" | `monitor.sh logs` | admin secret still default, or ARNs unset |
| Uploads fail | `monitor.sh logs` | IAM role missing S3/KMS perms, or `UPLOADS_BUCKET` unset |
| Domain won't go Active | `monitor.sh dns` | validation CNAMEs not in Route 53 yet / still propagating |
| TLS error | `monitor.sh dns` | App Runner cert still issuing (wait a few min) |

## Division of labor (who does what)

- **I drive:** all CLI steps (secrets, KMS, S3, IAM, WAF, Route 53 records),
  watching deploy status, reading logs, health/DNS/TLS checks, live smoke test.
- **You drive:** the App Runner **Console** GitHub-connection handshake (§5),
  and the final "does it look right" eyeball.
