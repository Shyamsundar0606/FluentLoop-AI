from datetime import datetime, timezone

from fastapi import APIRouter

from app.config import get_settings
from app.core.database import check_database_connection
from app.core.redis_client import check_redis_connection

settings = get_settings()
router = APIRouter(prefix="/health", tags=["health"])


@router.get("/live")
def live() -> dict:
    return {
        "status": "ok",
        "service": settings.app_name,
        "version": settings.app_version,
        "environment": settings.environment,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/ready")
def ready() -> dict:
    database_status = check_database_connection()
    redis_status = check_redis_connection()
    ready_state = "ok" if database_status and redis_status else "degraded"

    return {
        "status": ready_state,
        "service": settings.app_name,
        "database": {"status": "connected" if database_status else "unavailable"},
        "redis": {"status": "connected" if redis_status else "unavailable"},
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
