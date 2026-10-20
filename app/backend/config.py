"""Centralized runtime configuration with a local vs. AWS deployment switch.

A single environment variable, DEPLOY_MODE, selects the deployment profile:

  DEPLOY_MODE=local  (default)
    - SQLite file on local disk
    - Attachments stored in the local uploads/ directory
    - JWT secret + admin credentials from environment variables / dev defaults
    - No AWS calls, no boto3 required

  DEPLOY_MODE=aws
    - JWT secret and admin credentials pulled from AWS Secrets Manager
    - Attachments stored in / served from an S3 bucket (presigned URLs)
    - boto3 is imported lazily, only in this mode

The rest of the app imports from here and never branches on the mode directly,
so the local and AWS code paths stay identical apart from this module and
storage.py.
"""

import json
import os
from functools import lru_cache

DEPLOY_MODE = os.getenv("DEPLOY_MODE", "local").strip().lower()
IS_AWS = DEPLOY_MODE == "aws"

# AWS-mode configuration (all via environment variables so nothing is hardcoded).
AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
ADMIN_SECRET_ARN = os.getenv("ADMIN_SECRET_ARN", "")  # Secrets Manager ARN or name
JWT_SECRET_ARN = os.getenv("JWT_SECRET_ARN", "")  # Secrets Manager ARN or name
UPLOADS_BUCKET = os.getenv("UPLOADS_BUCKET", "")  # S3 bucket for attachments
PRESIGN_TTL_SECONDS = int(os.getenv("PRESIGN_TTL_SECONDS", "900"))

# Dev-only fallbacks (local mode only — never used when IS_AWS).
_LOCAL_JWT_DEFAULT = "change-me-in-production-use-openssl-rand-hex-32"
_LOCAL_ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin")
_LOCAL_ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "changeme")


@lru_cache(maxsize=1)
def _secrets_client():
    """Lazily create a Secrets Manager client (only imported in AWS mode)."""
    import boto3  # imported here so local mode never needs boto3

    return boto3.client("secretsmanager", region_name=AWS_REGION)


@lru_cache(maxsize=8)
def _get_secret_json(secret_id: str) -> dict:
    """Fetch and parse a JSON secret from Secrets Manager (cached per process)."""
    resp = _secrets_client().get_secret_value(SecretId=secret_id)
    return json.loads(resp["SecretString"])


@lru_cache(maxsize=8)
def _get_secret_string(secret_id: str) -> str:
    """Fetch a raw string secret from Secrets Manager (cached per process)."""
    resp = _secrets_client().get_secret_value(SecretId=secret_id)
    return resp["SecretString"]


def get_jwt_secret() -> str:
    """Return the JWT signing secret for the active mode."""
    if IS_AWS:
        if not JWT_SECRET_ARN:
            raise RuntimeError("DEPLOY_MODE=aws requires JWT_SECRET_ARN to be set")
        raw = _get_secret_string(JWT_SECRET_ARN)
        # Accept either a bare string secret or a JSON {"secret": "..."} shape.
        try:
            parsed = json.loads(raw)
            if isinstance(parsed, dict) and "secret" in parsed:
                return parsed["secret"]
        except (json.JSONDecodeError, TypeError):
            pass
        return raw
    return os.getenv("SECRET_KEY", _LOCAL_JWT_DEFAULT)


def get_admin_credentials() -> tuple[str, str]:
    """Return (username, password) used to seed/verify the admin account.

    In AWS mode these come from Secrets Manager and are required; the app will
    refuse to boot without them (see main.py). In local mode they fall back to
    dev defaults so local development is frictionless.
    """
    if IS_AWS:
        if not ADMIN_SECRET_ARN:
            raise RuntimeError("DEPLOY_MODE=aws requires ADMIN_SECRET_ARN to be set")
        data = _get_secret_json(ADMIN_SECRET_ARN)
        username = data.get("username")
        password = data.get("password")
        if not username or not password:
            raise RuntimeError(
                "Admin secret must contain non-empty 'username' and 'password' fields"
            )
        return username, password
    return _LOCAL_ADMIN_USERNAME, _LOCAL_ADMIN_PASSWORD


def summary() -> dict:
    """Non-sensitive config summary for /api/health and startup logging."""
    return {
        "mode": DEPLOY_MODE,
        "region": AWS_REGION if IS_AWS else None,
        "uploads_backend": "s3" if IS_AWS else "local",
        "uploads_bucket": UPLOADS_BUCKET if IS_AWS else None,
        "secrets_source": "secretsmanager" if IS_AWS else "env",
    }
