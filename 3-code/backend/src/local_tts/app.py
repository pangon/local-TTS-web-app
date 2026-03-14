"""FastAPI application factory and configuration."""

import logging
import sys
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from local_tts import config
from local_tts.api.router import api_router
from local_tts.api.sse import EventBus
from local_tts.db import init_db
from local_tts.services.model_service import ModelService
from local_tts.spa import SPAStaticFiles
from local_tts.tts.engine import TTSEngine
from local_tts.tts.ffmpeg_validator import FFmpegNotFoundError
from local_tts.tts.gpu_validator import GPUValidationError

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan: initialize resources on startup, clean up on shutdown."""
    # Step 1: Validate GPU/CUDA (REQ-F-gpu-validation)
    tts_engine = TTSEngine()
    try:
        gpu_info = tts_engine.validate_gpu()
    except GPUValidationError as exc:
        logger.error("GPU validation failed: %s", exc)
        print(f"\nERROR: {exc}\n", file=sys.stderr)
        sys.exit(1)

    logger.info(
        "GPU detected: %s (VRAM: %.0f MB total, %.0f MB free, CUDA %s)",
        gpu_info.name,
        gpu_info.vram_total_mb,
        gpu_info.vram_free_mb,
        gpu_info.cuda_version,
    )

    # Step 2: Validate ffmpeg (REQ-F-synthesize-audiobook — required for MP3 encoding)
    try:
        ffmpeg_path = tts_engine.validate_ffmpeg()
    except FFmpegNotFoundError as exc:
        logger.error("ffmpeg validation failed: %s", exc)
        print(f"\nERROR: {exc}\n", file=sys.stderr)
        sys.exit(1)

    logger.info("ffmpeg found: %s", ffmpeg_path)
    app.state.tts_engine = tts_engine
    app.state.event_bus = EventBus()
    app.state.model_service = ModelService(tts_engine, app.state.event_bus)

    # Step 3: Initialize database
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
