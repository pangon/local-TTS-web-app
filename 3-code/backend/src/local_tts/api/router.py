"""Top-level API router for /api/v1/."""

from fastapi import APIRouter

from local_tts.api.audiobooks import router as audiobooks_router
from local_tts.api.jobs import router as jobs_router
from local_tts.api.models import router as models_router
from local_tts.api.sse import router as sse_router

api_router = APIRouter()
api_router.include_router(sse_router)
api_router.include_router(models_router)
api_router.include_router(jobs_router)
api_router.include_router(audiobooks_router)


@api_router.get("/health")
async def health_check() -> dict:
    """Basic health check endpoint."""
    return {"status": "ok"}
