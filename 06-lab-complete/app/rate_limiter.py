"""Rate Limiter — Sliding window per user, stored in Redis (stateless)."""
import time
import redis
from fastapi import HTTPException

from app.config import settings

_redis: redis.Redis | None = None


def _get_redis() -> redis.Redis:
    global _redis
    if _redis is None:
        _redis = redis.from_url(settings.redis_url, decode_responses=True)
    return _redis


def check_rate_limit(user_key: str) -> None:
    """
    Sliding window rate limiter using Redis sorted sets.
    Raises HTTPException(429) if limit exceeded.
    """
    r = _get_redis()
    now = time.time()
    window_key = f"ratelimit:{user_key}"
    window_seconds = 60

    pipe = r.pipeline()
    # Remove expired entries
    pipe.zremrangebyscore(window_key, 0, now - window_seconds)
    # Count current entries
    pipe.zcard(window_key)
    # Add current request
    pipe.zadd(window_key, {str(now): now})
    # Set expiry on key
    pipe.expire(window_key, window_seconds + 1)
    results = pipe.execute()

    current_count = results[1]
    if current_count >= settings.rate_limit_per_minute:
        raise HTTPException(
            status_code=429,
            detail=f"Rate limit exceeded: {settings.rate_limit_per_minute} req/min. Try again later.",
            headers={"Retry-After": "60"},
        )
