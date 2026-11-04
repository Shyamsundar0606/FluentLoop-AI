from __future__ import annotations

from fastapi import HTTPException, Request, status

from app.core.redis_client import redis_client


def enforce_rate_limit(request: Request, action: str, limit: int, window_seconds: int) -> None:
    client_host = request.client.host if request.client else "unknown"
    key = f"fluentloop:ratelimit:{action}:{client_host}"
    try:
        count = int(redis_client.eval(
            "local count = redis.call('INCR', KEYS[1]); "
            "if count == 1 then redis.call('EXPIRE', KEYS[1], ARGV[1]); end; "
            "return count",
            1,
            key,
            window_seconds,
        ))
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication services are temporarily unavailable.",
            headers={"Retry-After": str(window_seconds)},
        ) from exc

    if count > limit:
        ttl = redis_client.ttl(key)
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many requests. Please try again later.",
            headers={"Retry-After": str(max(ttl, 1))},
        )
