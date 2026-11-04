from __future__ import annotations

import redis

from app.config import get_settings

settings = get_settings()
redis_client = redis.Redis.from_url(settings.redis_url, decode_responses=True)


def check_redis_connection() -> bool:
    try:
        return bool(redis_client.ping())
    except Exception:
        return False
