# Configuration & Deployment Modes

The Life Plan Tracker runs the **same codebase** in two modes, selected by a
single environment variable: **`DEPLOY_MODE`** (`local` | `aws`). You develop
locally, push to GitHub, and AWS builds and runs the image in `aws` mode. No
code edits are needed to switch.

## The switch

| Concern | `DEPLOY_MODE=local` (default) | `DEPLOY_MODE=aws` |
|---------|-------------------------------|-------------------|
| JWT signing secret | `SECRET_KEY` env var / dev default | AWS Secrets Manager (`JWT_SECRET_ARN`) |
| Admin credentials | `ADMIN_USERNAME` / `ADMIN_PASSWORD` (default `admin`/`changeme`) | AWS Secrets Manager (`ADMIN_SECRET_ARN`) — **boot refused if still default** |
| Attachment storage | local `uploads/` directory | private S3 bucket (`UPLOADS_BUCKET`), served via presigned URLs |
| boto3 / AWS calls | none (boto3 imported lazily, never in local) | Secrets Manager + S3 |
| `/api/health` reports | `mode: local` | `mode: aws` + region/bucket |

All of this lives in `app/backend/config.py` and `app/backend/storage.py`. The
rest of the app never branches on the mode, so the two paths stay identical.

## Local development

```bash
cd app/backend
cp .env.example .env          # optional; defaults work out of the box
source ../../.venv/bin/activate
uvicorn main:app --host 0.0.0.0 --port 8000
```

- Uses SQLite (`life_plan.db`), local `uploads/`, and `admin` / `changeme`.
- `GET /api/health` returns `{"status":"ok","config":{"mode":"local",...}}`.
- Nothing touches AWS.

## The local → GitHub → AWS flow

1. **Develop locally** in `local` mode; run the Playwright suite
   (`cd app/frontend && npm test`) before pushing.
2. **Push to GitHub.** The repo holds source only — no built `dist/`, no DB, no
   uploads (see `.dockerignore` / `.gitignore`).
3. **AWS builds the image** from the repo using the root `Dockerfile`
   (stage 1 builds the React frontend, stage 2 runs FastAPI serving both the
   API and the SPA on port 8000). The image defaults to `DEPLOY_MODE=aws`.
4. **AWS App Runner runs the image** with these environment variables:

   | Variable | Value |
   |----------|-------|
   | `DEPLOY_MODE` | `aws` |
   | `AWS_REGION` | `us-east-1` |
   | `ADMIN_SECRET_ARN` | `arn:aws:secretsmanager:us-east-1:<ACCOUNT_ID>:secret:life-planning/admin-credentials-XXXXXX` |
   | `JWT_SECRET_ARN` | *(created during infra bring-up)* |
   | `UPLOADS_BUCKET` | *(created during infra bring-up)* |
   | `PRESIGN_TTL_SECONDS` | `900` |

   App Runner's instance role must allow `secretsmanager:GetSecretValue` on the
   two secret ARNs, `s3:GetObject/PutObject/DeleteObject` on the uploads bucket,
   and `kms:Decrypt/Encrypt` on the multi-region key.

5. **App Runner health check** targets `/api/health`.

## Security behaviors baked in

- In `aws` mode the app **refuses to start** if the admin credential is still
  `admin`/`changeme`, so it can never be exposed with the default login.
- In `aws` mode the admin credential is **re-synced from Secrets Manager on
  every boot**, so rotating the secret rotates the login (idempotent).
- The JWT secret is never hardcoded; it is read from Secrets Manager in `aws`
  mode.
- `.env`, `life_plan.db`, and `uploads/` are git-ignored and docker-ignored.

## Admin credential already provisioned

A strong (43-char, 256-bit) random admin password is already stored at:

```
arn:aws:secretsmanager:us-east-1:<ACCOUNT_ID>:secret:life-planning/admin-credentials-XXXXXX
```

Retrieve it when needed:

```bash
aws secretsmanager get-secret-value \
  --secret-id life-planning/admin-credentials \
  --region us-east-1 --query SecretString --output text
```
