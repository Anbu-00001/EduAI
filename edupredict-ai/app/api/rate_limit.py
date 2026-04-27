"""
Redis-backed sliding window rate limiter.

Algorithm: Fixed window counter (simple, O(1) per request)
  - Key: f"ratelimit:{tenant_id}:{current_minute}"
  - Value: request count in current minute window
  - TTL: 90 seconds (covers window + grace)
  
  This approach gives exactly N requests per 60-second window.
  Does not prevent burst at window boundary — acceptable for B2B API
  where clients are known trusted entities, not anonymous users.
  
  For stricter burst control: use sliding window log (O(n) per request)
  or token bucket (O(1) with clock synchronisation).
"""

import time
import logging
from fastapi import HTTPException, Request
import redis.asyncio as aioredis
import os

logger = logging.getLogger(__name__)

REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
_redis_client = None


async def get_redis():
    global _redis_client
    if _redis_client is None:
        _redis_client = aioredis.from_url(REDIS_URL, decode_responses=True)
    return _redis_client


async def check_rate_limit(tenant_id: str, limit_rpm: int, request: Request):
    """
    FastAPI dependency: raises 429 if rate limit exceeded.
    Attaches rate limit headers to request state for response middleware.
    """
    try:
        r = await get_redis()
        minute_key = f"ratelimit:{tenant_id}:{int(time.time() // 60)}"

        pipe = r.pipeline()
        pipe.incr(minute_key)
        pipe.expire(minute_key, 90)
        results = await pipe.execute()

        current_count = results[0]
        remaining = max(0, limit_rpm - current_count)
        reset_at = (int(time.time() // 60) + 1) * 60

        # Attach to request state for response headers
        request.state.rate_limit_remaining = remaining
        request.state.rate_limit_reset = reset_at
        request.state.rate_limit_limit = limit_rpm

        if current_count > limit_rpm:
            logger.warning(
                f"Rate limit exceeded: tenant={tenant_id}, "
                f"count={current_count}, limit={limit_rpm}"
            )
            raise HTTPException(
                status_code=429,
                detail={
                    "error": "rate_limit_exceeded",
                    "message": f"Limit: {limit_rpm} requests/minute",
                    "retry_after_seconds": reset_at - int(time.time()),
                },
                headers={"Retry-After": str(reset_at - int(time.time()))}
            )
    except HTTPException:
        raise
    except Exception as e:
        # Redis unavailable — fail open (don't block requests)
        logger.error(f"Rate limiter error (failing open): {e}")
