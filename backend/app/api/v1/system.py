from datetime import datetime, timezone

from fastapi import APIRouter

from app.config import get_settings

settings = get_settings()
router = APIRouter(tags=["system"])


@router.get("/system/info")
def system_info() -> dict:
    return {
        "app_name": settings.app_name,
        "version": settings.app_version,
        "environment": settings.environment,
        "api_version": "v1",
        "features": [
            "frontend foundation",
            "backend foundation",
            "postgresql foundation",
            "redis foundation",
            "docker orchestration",
        ],
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
