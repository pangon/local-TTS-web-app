"""FastAPI application factory and configuration."""

from fastapi import FastAPI

from local_tts.api.router import api_router


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(title="Local TTS Web App", version="0.1.0")
    app.include_router(api_router, prefix="/api/v1")
    return app


app = create_app()
