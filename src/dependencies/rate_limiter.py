import time
import uuid

from fastapi import Depends, HTTPException, Request

from src.core.redis_client import redis_client
from src.dependencies.auth import get_current_user


async def check_rate_limit(key: str, limit: int, window: int):
    """
    Checks rate limit using a sliding window log via Redis sorted sets.
    Raises HTTPException 429 if the count exceeds the limit.
    """
    now = time.time()
    redis_key = f"rate_limit:{key}"
    member = f"{now}_{uuid.uuid4().hex}"

    pipe = redis_client.pipeline()
    # Remove timestamps older than the window
    pipe.zremrangebyscore(redis_key, 0, now - window)
    # Add current timestamp
    pipe.zadd(redis_key, {member: now})
    # Count members in sorted set
    pipe.zcard(redis_key)
    # Refresh key expiry
    pipe.expire(redis_key, window)

    results = pipe.execute()
    count = results[2]

    if count > limit:
        raise HTTPException(
            status_code=429, detail="Too many requests. Please try again later."
        )


async def buy_rate_limiter(
    request: Request, user_id: str = Depends(get_current_user)
) -> str:
    """
    Rate limiter for the buy route.
    Limits:
      - 3 requests per 10 seconds per user_id.
      - 10 requests per 10 seconds per IP address.
    """
    ip = request.client.host if request.client else "unknown"

    # 1. User limit
    await check_rate_limit(f"buy:user:{user_id}", limit=3, window=10)
    # 2. IP limit
    await check_rate_limit(f"buy:ip:{ip}", limit=10, window=10)

    return user_id


async def login_rate_limiter(request: Request):
    """
    Rate limiter for the login route.
    Limits:
      - 5 requests per 10 seconds per IP address.
    """
    ip = request.client.host if request.client else "unknown"
    await check_rate_limit(f"login:ip:{ip}", limit=5, window=10)
