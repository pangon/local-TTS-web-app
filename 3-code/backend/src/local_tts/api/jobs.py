"""Synthesis job API endpoints.

Provides the REST endpoint for creating audiobook synthesis jobs
(REQ-F-upload-text-file, REQ-F-disk-space-preflight).
"""

from __future__ import annotations

import logging
import shutil

from fastapi import APIRouter, Form, HTTPException, Request, UploadFile
from pydantic import BaseModel

from local_tts.services.job_service import JobService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/jobs")

MAX_FILE_SIZE_BYTES = 2 * 1024 * 1024  # 2 MB (REQ-F-upload-text-file)

# Heuristic for estimating output audio size from text length.
# ~150 words/min at ~5 chars/word = 750 chars/min of audio.
# MP3 at ~128 kbps ≈ 0.96 MB/min.
# Factor: 0.96 / 750 ≈ 0.00128 MB per character.
# Apply 1.5× safety margin → ~0.002 MB per character.
_AUDIO_MB_PER_CHAR = 0.002


class SynthesisJobResponse(BaseModel):
    id: str
    type: str
    status: str
    progress: int
    created_at: str


class InsufficientDiskSpaceDetail(BaseModel):
    detail: str
    estimated_mb: float
    available_mb: float


def _get_job_service(request: Request) -> JobService:
    return request.app.state.job_service


def _estimate_audio_mb(text_length: int) -> float:
    """Estimate output audio size in MB from text character count."""
    return max(text_length * _AUDIO_MB_PER_CHAR, 1.0)


@router.post("/synthesis", status_code=201)
async def create_synthesis_job(
    request: Request,
    file: UploadFile,
    voice: str | None = Form(default=None),
    language: str | None = Form(default=None),
) -> SynthesisJobResponse:
    """Upload a .txt file and start audiobook synthesis.

    Validates file type and size (REQ-F-upload-text-file), checks that a model
    is loaded, performs disk space preflight (REQ-F-disk-space-preflight), then
    queues the job for background processing.
    """
    # --- File validation (REQ-F-upload-text-file) ---

    filename = file.filename or ""
    if not filename.lower().endswith(".txt"):
        raise HTTPException(
            status_code=400,
            detail="Invalid file type: only .txt files are accepted",
        )

    content_bytes = await file.read()

    if len(content_bytes) > MAX_FILE_SIZE_BYTES:
        raise HTTPException(
            status_code=400,
            detail=f"File exceeds the 2 MB size limit ({len(content_bytes)} bytes)",
        )

    try:
        text = content_bytes.decode("utf-8")
    except UnicodeDecodeError:
        raise HTTPException(
            status_code=400,
            detail="File is not valid UTF-8 encoded text",
        )

    if not text.strip():
        raise HTTPException(status_code=400, detail="File is empty")

    # --- Model loaded check ---

    tts_engine = request.app.state.tts_engine
    if tts_engine.loaded_model_id is None:
        raise HTTPException(status_code=409, detail="No model loaded")

    # --- Disk space preflight (REQ-F-disk-space-preflight) ---

    data_dir = request.app.state.job_service._data_dir
    estimated_mb = _estimate_audio_mb(len(text))

    try:
        disk = shutil.disk_usage(data_dir)
    except OSError:
        disk = shutil.disk_usage(data_dir.parent)

    available_mb = disk.free / (1024 * 1024)

    if estimated_mb > available_mb:
        raise HTTPException(
            status_code=409,
            detail={
                "detail": "Insufficient disk space",
                "estimated_mb": round(estimated_mb, 1),
                "available_mb": round(available_mb, 1),
            },
        )

    # --- Create and enqueue job ---

    job_service = _get_job_service(request)
    job = job_service.create_synthesis_job(
        source_filename=filename,
        text=text,
        voice=voice,
        language=language,
    )

    logger.info(
        "Synthesis job %s created via API (file=%s, %d chars)",
        job.id,
        filename,
        len(text),
    )

    return SynthesisJobResponse(
        id=job.id,
        type=job.type,
        status=job.status,
        progress=job.progress,
        created_at=job.created_at,
    )
