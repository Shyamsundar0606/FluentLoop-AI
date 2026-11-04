import asyncio
from contextlib import asynccontextmanager
from starlette.concurrency import run_in_threadpool


@asynccontextmanager
async def lifespan(app):
    from app.core.database import get_db, SessionLocal
    from app.speech.storage import cleanup

    if get_db in app.dependency_overrides:
        yield
        return

    def sweep():
        with SessionLocal() as db:
            cleanup(db)

    async def loop():
        while True:
            try:
                await run_in_threadpool(sweep)
            except Exception:
                import logging

                logging.getLogger(__name__).warning(
                    "speech_retention_cleanup_unavailable"
                )
            await asyncio.sleep(60)

    task = asyncio.create_task(loop())
    try:
        yield
    finally:
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
