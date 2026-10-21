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

# Install Litestream (SQLite -> S3 continuous replication) so the DB survives
# App Runner's ephemeral container filesystem across redeploys.
ADD https://github.com/benbjohnson/litestream/releases/download/v0.3.13/litestream-v0.3.13-linux-amd64.tar.gz /tmp/litestream.tar.gz
RUN tar -C /usr/local/bin -xzf /tmp/litestream.tar.gz && rm /tmp/litestream.tar.gz

# Copy backend source.
COPY app/backend/ ./

# Copy the built frontend into the location main.py serves from
# (FRONTEND_DIR = app/frontend/dist relative to the backend).
COPY --from=frontend /build/frontend/dist /app/frontend/dist

RUN chmod +x /app/backend/entrypoint.sh

EXPOSE 8000

# Entrypoint restores the DB from S3 (if DB_REPLICA_BUCKET set) and runs the
# app under Litestream replication; falls back to plain uvicorn locally.
# App Runner health check should target /api/health.
CMD ["/app/backend/entrypoint.sh"]
