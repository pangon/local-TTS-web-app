"""Top-level API router for /api/v1/."""

from fastapi import APIRouter

api_router = APIRouter()


@api_router.get("/health")
async def health_check() -> dict:
    """Basic health check endpoint."""
    return {"status": "ok"}
