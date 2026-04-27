"""
B2B API Authentication for EduPredict AI

Two auth modes:
1. API Key (for lender integrations): stateless, per-tenant key
   Header: X-API-Key: <key>
   
2. JWT Bearer (for dashboard): short-lived tokens (1 hour)
   Header: Authorization: Bearer <jwt>

API keys are stored as SHA-256 hashes in PostgreSQL.
The plaintext key is shown ONCE at creation and never stored.
This follows the same model as GitHub personal access tokens.

Rate limiting is applied per API key (not per IP):
  Default: 100 requests/minute
  Override configurable per-tenant in api_keys table
"""

import hashlib
import os
import secrets
import time
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional
from fastapi import HTTPException, Security, Depends, Request
from fastapi.security import APIKeyHeader, HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
import asyncpg

logger = logging.getLogger(__name__)

JWT_SECRET = os.environ.get("JWT_SECRET", "change_this_in_production_placeholder_32chars")
JWT_ALGORITHM = "HS256"
JWT_EXPIRY_HOURS = 1

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)
bearer_scheme = HTTPBearer(auto_error=False)


def hash_api_key(plaintext_key: str) -> str:
    """SHA-256 of the raw key. Never store plaintext."""
    return hashlib.sha256(plaintext_key.encode()).hexdigest()


def generate_api_key() -> tuple[str, str]:
    """
    Generate a new API key.
    Returns: (plaintext_key, key_hash)
    plaintext_key is shown once; key_hash stored in DB.
    """
    plaintext = f"ep_{secrets.token_urlsafe(32)}"
    return plaintext, hash_api_key(plaintext)


def create_jwt_token(tenant_id: str) -> str:
    payload = {
        "sub": tenant_id,
        "iat": datetime.now(timezone.utc),
        "exp": datetime.now(timezone.utc) + timedelta(hours=JWT_EXPIRY_HOURS),
        "type": "access",
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def verify_jwt_token(token: str) -> dict:
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except JWTError as e:
        raise HTTPException(status_code=401, detail=f"Invalid token: {e}")


async def get_current_tenant(
    request: Request,
    api_key: Optional[str] = Security(api_key_header),
    credentials: Optional[HTTPAuthorizationCredentials] = Security(bearer_scheme),
) -> dict:
    """
    FastAPI dependency: resolves tenant from either API key or JWT.
    Returns tenant dict with {tenant_id, rate_limit, permissions}.
    Raises 401 if neither is valid.
    """
    db_pool = request.app.state.db_pool

    if api_key:
        key_hash = hash_api_key(api_key)
        async with db_pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT tenant_id, rate_limit_rpm, active "
                "FROM api_keys WHERE key_hash = $1",
                key_hash
            )
        if not row or not row["active"]:
            raise HTTPException(status_code=401, detail="Invalid API key")
        return {
            "tenant_id": row["tenant_id"],
            "rate_limit_rpm": row["rate_limit_rpm"],
            "auth_method": "api_key",
        }

    if credentials:
        payload = verify_jwt_token(credentials.credentials)
        return {
            "tenant_id": payload["sub"],
            "rate_limit_rpm": 60,   # Default for JWT auth (dashboard users)
            "auth_method": "jwt",
        }

    raise HTTPException(
        status_code=401,
        detail="Authentication required: X-API-Key header or Bearer token"
    )
