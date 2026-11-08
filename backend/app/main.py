from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.v1.health import router as health_router
from app.api.v1.system import router as system_router
from app.api.v1.auth import router as auth_router
from app.api.v1.users import router as users_router
from app.api.v1.curriculum import router as curriculum_router
from app.api.v1.content_review import router as content_review_router
from app.api.v1.learning import router as learning_router
from app.api.v1.ai import router as ai_router
from app.api.v1.speech import router as speech_router
from app.api.v1.study import router as study_router
from app.speech.lifecycle import lifespan as speech_lifespan
from app.config import get_settings
from app.logging_config import configure_logging

settings = get_settings()
configure_logging(settings.log_level)

app = FastAPI(
    lifespan=speech_lifespan,
    title=settings.app_name,
    version=settings.app_version,
    description="Foundation API for FluentLoop AI.",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["Retry-After"],
)

app.include_router(health_router, prefix=settings.api_prefix)
app.include_router(study_router, prefix=settings.api_prefix)
app.include_router(system_router, prefix=settings.api_prefix)
app.include_router(auth_router, prefix=settings.api_prefix)
app.include_router(users_router, prefix=settings.api_prefix)
app.include_router(curriculum_router, prefix=settings.api_prefix)
app.include_router(content_review_router, prefix=settings.api_prefix)
app.include_router(learning_router, prefix=settings.api_prefix)
app.include_router(ai_router, prefix=settings.api_prefix)
app.include_router(speech_router, prefix=settings.api_prefix)


@app.middleware("http")
async def private_api_responses(request, call_next):
    if request.url.path.startswith(f"{settings.api_prefix}/speech") and request.method in {"POST", "PATCH", "DELETE"}:
        body = bytearray()
        async for chunk in request.stream():
            body.extend(chunk)
            if len(body) > settings.speech_max_upload_bytes + 16000:
                return JSONResponse(status_code=413, content={"detail": "Speech request body is too large."}, headers={"Cache-Control": "no-store"})
        request._body = bytes(body)
    if request.url.path.startswith(f"{settings.api_prefix}/ai") and request.method in {"POST", "PATCH"}:
        body = bytearray()
        async for chunk in request.stream():
            body.extend(chunk)
            if len(body) > 32000:
                return JSONResponse(status_code=413, content={"detail": "AI request body is too large."}, headers={"Cache-Control": "no-store"})
        request._body = bytes(body)
    response = await call_next(request)
    private_prefixes = (
        f"{settings.api_prefix}/auth",
        f"{settings.api_prefix}/users",
        f"{settings.api_prefix}/levels",
        f"{settings.api_prefix}/courses",
        f"{settings.api_prefix}/units",
        f"{settings.api_prefix}/lessons",
        f"{settings.api_prefix}/vocabulary",
        f"{settings.api_prefix}/verbs",
        f"{settings.api_prefix}/grammar",
        f"{settings.api_prefix}/dialogues",
        f"{settings.api_prefix}/learning",
        f"{settings.api_prefix}/ai",
        f"{settings.api_prefix}/speech",
        f"{settings.api_prefix}/study",
        f"{settings.api_prefix}/review",
        f"{settings.api_prefix}/content-review",
    )
    if request.url.path.startswith(private_prefixes):
        response.headers["Cache-Control"] = "no-store"
        response.headers["Pragma"] = "no-cache"
    return response


@app.get("/")
def root() -> dict:
    return {
        "service": settings.app_name,
        "status": "online",
        "version": settings.app_version,
    }
