"""FastAPI application factory and configuration."""

import asyncio
import logging
import sys
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from local_tts import config
from local_tts.api.router import api_router
from local_tts.api.sse import EventBus
from local_tts.db import init_db
from local_tts.services.job_service import JobService, SynthesisJobResult
from local_tts.services.library_service import LibraryService
from local_tts.preprocessing import PreprocessingService
from local_tts.services.model_service import ModelService
from local_tts.services.playback_service import PlaybackService
from local_tts.spa import SPAStaticFiles
from local_tts.tts.engine import TTSEngine
from local_tts.tts.ffmpeg_validator import FFmpegNotFoundError
from local_tts.tts.gpu_validator import GPUValidationError

logger = logging.getLogger(__name__)


def _publish_from_thread(
    event_bus: EventBus,
    loop: asyncio.AbstractEventLoop,
    event_type: str,
    data: dict[str, Any],
) -> None:
    """Publish an SSE event from a background thread (DEC-sse-progress)."""
    asyncio.run_coroutine_threadsafe(
        event_bus.publish(event_type, data),
        loop,
    )


def _wire_job_callbacks(
    job_service: JobService,
    library_service: LibraryService,
    event_bus: EventBus,
    loop: asyncio.AbstractEventLoop,
) -> None:
    """Connect JobService callbacks to LibraryService and SSE EventBus.

    Called during lifespan after all services are ready.  Callbacks are
    invoked from the job worker thread.  The completion handler persists
    audiobook records first (TASK-library-service-create), then publishes
    the SSE event so the frontend receives the audiobook_id only after
    it is committed to the database.
    """

    def on_progress(job_id: str, job_type: str, progress: int) -> None:
        _publish_from_thread(event_bus, loop, "job-progress", {
            "job_id": job_id,
            "type": job_type,
            "status": "processing",
            "progress": progress,
        })

    def on_completed(result: SynthesisJobResult) -> None:
        library_service.create_audiobook_from_job(result)
        _publish_from_thread(event_bus, loop, "job-completed", {
            "job_id": result.job_id,
            "type": "synthesis",
            "audiobook_id": result.audiobook_id,
        })

    def on_failed(job_id: str, job_type: str, error_message: str) -> None:
        _publish_from_thread(event_bus, loop, "job-failed", {
            "job_id": job_id,
            "type": job_type,
            "error_message": error_message,
        })

    job_service.on_progress = on_progress
    job_service.on_completed = on_completed
    job_service.on_failed = on_failed


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

    # Step 4: Initialize Job Service (DEC-single-process — background thread)
    job_service = JobService(tts_engine, conn, config.DATA_DIR)
    app.state.job_service = job_service

    # Step 5: Initialize Library Service (TASK-library-service-create)
    library_service = LibraryService(config.DATA_DIR)
    app.state.library_service = library_service

    # Step 5b: Initialize Playback Service (TASK-playback-position-api)
    app.state.playback_service = PlaybackService(config.DATA_DIR)

    # Step 5c: Initialize Preprocessing Service (TASK-preprocess-api).
    # Synchronous, GPU-agnostic text normalization (DEC-text-preprocessing-pipeline);
    # the optional domain dictionary is loaded from the configured default path
    # and its absence does not break preprocessing.
    app.state.preprocessing_service = PreprocessingService()

    # Step 6: Wire job callbacks to Library Service and SSE EventBus
    _wire_job_callbacks(
        job_service, library_service, app.state.event_bus,
        asyncio.get_running_loop(),
    )

    yield

    await app.state.event_bus.shutdown()
    job_service.shutdown()
    conn.close()


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(title="Local TTS Web App", version="0.1.0", lifespan=lifespan)
    app.include_router(api_router, prefix="/api/v1")

    if config.STATIC_DIR.is_dir():
        app.mount("/", SPAStaticFiles(directory=config.STATIC_DIR, html=True), name="spa")

    return app


app = create_app()
