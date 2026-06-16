"""Synthesis job API endpoints.

Provides the REST endpoint for creating audiobook synthesis jobs from the
confirmed normalized text returned by ``POST /preprocess`` and approved by the
user (REQ-F-synthesize-audiobook, REQ-USA-normalized-text-review,
DEC-preprocess-review-flow).

The ``.txt`` upload and all text normalization happen earlier at
``POST /preprocess``; this endpoint receives the reviewed text as JSON and
synthesizes **exactly** that text — it does **not** re-run the preprocessing
pipeline. A disk-space preflight check (REQ-F-disk-space-preflight) derives its
estimate from the text length before queuing the job.
"""

from __future__ import annotations

import logging
import shutil

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from local_tts.services.job_service import JobService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/jobs")

# Heuristic for estimating output audio size from text length.
# ~150 words/min at ~5 chars/word = 750 chars/min of audio.
# MP3 at ~128 kbps ≈ 0.96 MB/min.
# Factor: 0.96 / 750 ≈ 0.00128 MB per character.
# Apply 1.5× safety margin → ~0.002 MB per character.
_AUDIO_MB_PER_CHAR = 0.002


class SynthesisJobRequest(BaseModel):
    """Request body for ``POST /jobs/synthesis`` (confirmed normalized text).

    The ``text`` is the exact normalized text the user reviewed and confirmed
    after ``POST /preprocess`` (DEC-preprocess-review-flow); it is synthesized
    as-is with no further preprocessing.
    """

    text: str
    source_filename: str
    voice: str | None = None
    language: str | None = None


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
    body: SynthesisJobRequest,
) -> SynthesisJobResponse:
    """Start audiobook synthesis from confirmed normalized text.

    Receives the reviewed text as JSON (DEC-preprocess-review-flow), checks that
    a model is loaded, performs a disk-space preflight derived from the text
    length (REQ-F-disk-space-preflight), then queues the job for background
    processing. The text is synthesized exactly as provided — preprocessing is
    not re-run (REQ-USA-normalized-text-review).
    """
    # --- Input validation ---

    text = body.text
    if not text.strip():
        raise HTTPException(status_code=400, detail="Text is empty")

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
        source_filename=body.source_filename,
        text=text,
        voice=body.voice,
        language=body.language,
    )

    logger.info(
        "Synthesis job %s created via API (source=%s, %d chars)",
        job.id,
        body.source_filename,
        len(text),
    )

    return SynthesisJobResponse(
        id=job.id,
        type=job.type,
        status=job.status,
        progress=job.progress,
        created_at=job.created_at,
    )
