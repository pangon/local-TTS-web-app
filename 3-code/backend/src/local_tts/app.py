"""FastAPI application factory and configuration."""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from local_tts import config
from local_tts.api.router import api_router
from local_tts.db import init_db
from local_tts.spa import SPAStaticFiles


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan: initialize resources on startup, clean up on shutdown."""
    conn = init_db(config.DATA_DIR)
    app.state.db_conn = conn
    yield
    conn.close()


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(title="Local TTS Web App", version="0.1.0", lifespan=lifespan)
    app.include_router(api_router, prefix="/api/v1")

    if config.STATIC_DIR.is_dir():
        app.mount("/", SPAStaticFiles(directory=config.STATIC_DIR, html=True), name="spa")

    return app


app = create_app()
