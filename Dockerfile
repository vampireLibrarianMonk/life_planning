# Life Plan Tracker — single-image build for AWS App Runner.
#
# Stage 1 builds the React frontend; stage 2 runs the FastAPI backend which
# serves both the API and the built SPA on port 8000. The deployment mode is
# selected at runtime via the DEPLOY_MODE env var (local|aws) — see
# app/backend/config.py. For AWS App Runner, set DEPLOY_MODE=aws and provide
# ADMIN_SECRET_ARN / JWT_SECRET_ARN / UPLOADS_BUCKET / AWS_REGION.

# ---- Stage 1: build frontend ----
FROM node:22-alpine AS frontend
WORKDIR /build/frontend
COPY app/frontend/package.json app/frontend/package-lock.json ./
RUN npm ci
COPY app/frontend/ ./
RUN npm run build
# Produces /build/frontend/dist

# ---- Stage 2: backend runtime ----
FROM python:3.12-slim AS runtime
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DEPLOY_MODE=aws

WORKDIR /app/backend

# Install backend deps (includes boto3 for AWS mode).
COPY app/backend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# curl + ca-certificates are needed to fetch + checksum-verify Litestream below;
# removed in the same layer to keep the runtime image lean.
# hadolint ignore=DL3008
RUN apt-get update \
    && apt-get install -y --no-install-recommends curl ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Install Litestream (SQLite -> S3 continuous replication) so the DB survives
# App Runner's ephemeral container filesystem across redeploys.
# SECURITY: pin + verify the release checksum before extracting (the binary runs
# with the instance role's AWS creds, so a tampered/retagged asset = RCE).
# Upgraded to v0.5.17 (2026-10-31) — the old v0.3.13 build triggered ~60 Trivy
# findings from its stale Go stdlib/x-crypto; v0.5.17 is built with a current Go.
# SHA256 is for the official v0.5.17 linux-x86_64 release artifact.
# pipefail so a failed download/checksum aborts the piped sha256sum -c.
SHELL ["/bin/bash", "-o", "pipefail", "-c"]
ARG LITESTREAM_VERSION=0.5.17
ARG LITESTREAM_SHA256=cfb371176d164437ae869f8351cfde49bd1804ae71c61923f75c9cba9c9c006d
RUN set -eux; \
    curl -fsSL -o /tmp/litestream.tar.gz \
      "https://github.com/benbjohnson/litestream/releases/download/v${LITESTREAM_VERSION}/litestream-${LITESTREAM_VERSION}-linux-x86_64.tar.gz"; \
    echo "${LITESTREAM_SHA256}  /tmp/litestream.tar.gz" | sha256sum -c -; \
    tar -C /usr/local/bin -xzf /tmp/litestream.tar.gz; \
    rm /tmp/litestream.tar.gz

# Copy backend source.
COPY app/backend/ ./

# Copy the built frontend into the location main.py serves from
# (FRONTEND_DIR = app/frontend/dist relative to the backend).
COPY --from=frontend /build/frontend/dist /app/frontend/dist

RUN chmod +x /app/backend/entrypoint.sh

# SECURITY: run as a non-root user. The app writes the SQLite DB + uploads under
# /app/backend at runtime (Litestream restores there), so grant ownership of /app.
RUN useradd -r -u 10001 -d /app appuser \
    && mkdir -p /app/backend/uploads \
    && chown -R appuser:appuser /app
USER 10001

EXPOSE 8000

# Entrypoint restores the DB from S3 (if DB_REPLICA_BUCKET set) and runs the
# app under Litestream replication; falls back to plain uvicorn locally.
# App Runner health check should target /api/health.
CMD ["/app/backend/entrypoint.sh"]
