"""Cost Guard — $10/month per user budget, stored in Redis (stateless)."""
import redis
from datetime import datetime
from fastapi import HTTPException

from app.config import settings

_redis: redis.Redis | None = None


def _get_redis() -> redis.Redis:
    global _redis
    if _redis is None:
        _redis = redis.from_url(settings.redis_url, decode_responses=True)
    return _redis


def check_budget(user_key: str, estimated_cost: float = 0.0) -> None:
    """
    Check if user still has budget this month.
    Raises HTTPException(402) if monthly budget exceeded.
    """
    r = _get_redis()
    month_key = datetime.utcnow().strftime("%Y-%m")
    budget_key = f"budget:{user_key}:{month_key}"

    current = float(r.get(budget_key) or 0)
    if current + estimated_cost > settings.monthly_budget_usd:
        raise HTTPException(
            status_code=402,
            detail=f"Monthly budget ${settings.monthly_budget_usd} exceeded. Current: ${current:.4f}",
        )


def record_cost(user_key: str, cost: float) -> None:
    """Record cost for a user in the current month."""
    r = _get_redis()
    month_key = datetime.utcnow().strftime("%Y-%m")
    budget_key = f"budget:{user_key}:{month_key}"

    r.incrbyfloat(budget_key, cost)
    r.expire(budget_key, 32 * 24 * 3600)  # 32 days TTL
