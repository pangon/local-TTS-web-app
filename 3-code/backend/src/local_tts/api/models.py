"""Model management API endpoints.

Provides REST endpoints for listing, downloading, and loading TTS models
(REQ-F-model-listing, REQ-F-model-download, REQ-F-gpu-validation).
"""

from __future__ import annotations

import asyncio
import logging

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from local_tts.services.model_service import InsufficientVRAMError, ModelService
from local_tts.tts.model_loader import ModelLoadError

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/models")


class ModelResponse(BaseModel):
    model_id: str
    name: str
    is_cached: bool
    is_loaded: bool
    loader_available: bool
    license: str
    license_is_foss: bool
    license_notice: str | None


class DownloadResponse(BaseModel):
    model_id: str
    status: str


class LoadResponse(BaseModel):
    model_id: str
    status: str


class InsufficientSpaceDetail(BaseModel):
    detail: str
    estimated_mb: float
    available_mb: float


class InsufficientVRAMDetail(BaseModel):
    detail: str
    required_mb: float
    available_mb: float


def _get_model_service(request: Request) -> ModelService:
    """Retrieve the ModelService from app state."""
    return request.app.state.model_service


@router.get("")
async def list_models(request: Request) -> list[ModelResponse]:
    """List compatible HuggingFace TTS models with cache and load status."""
    service = _get_model_service(request)
    models = service.list_models()
    return [
        ModelResponse(
            model_id=m.model_id,
            name=m.name,
            is_cached=m.is_cached,
            is_loaded=m.is_loaded,
            loader_available=m.loader_available,
            license=m.license,
            license_is_foss=m.license_is_foss,
            license_notice=m.license_notice,
        )
        for m in models
    ]


@router.post("/{model_id:path}/download", status_code=202)
async def download_model(model_id: str, request: Request) -> DownloadResponse:
    """Start downloading a model to the local cache.

    Returns 202 immediately. Progress is reported via SSE events
    (download-progress, download-completed, download-failed).
    """
    service = _get_model_service(request)

    if service.is_model_cached(model_id):
        raise HTTPException(status_code=409, detail="Model already cached")

    if service.is_downloading(model_id):
        raise HTTPException(status_code=409, detail="Download already in progress")

    disk_check = service.check_disk_space(model_id)
    if not disk_check.sufficient:
        raise HTTPException(
            status_code=409,
            detail={
                "detail": "Insufficient disk space",
                "estimated_mb": disk_check.estimated_mb,
                "available_mb": disk_check.available_mb,
            },
        )

    loop = asyncio.get_running_loop()
    service.start_download(model_id, loop)

    return DownloadResponse(model_id=model_id, status="downloading")


@router.post("/{model_id:path}/load")
async def load_model(model_id: str, request: Request) -> LoadResponse:
    """Load a cached model onto the GPU.

    Synchronous — returns when the model is loaded and ready for inference.
    Checks VRAM availability before loading.
    """
    service = _get_model_service(request)

    if not service.is_model_cached(model_id):
        raise HTTPException(status_code=404, detail="Model not cached")

    try:
        service.load_model(model_id)
    except InsufficientVRAMError as exc:
        raise HTTPException(
            status_code=409,
            detail={
                "detail": "Insufficient VRAM",
                "required_mb": round(exc.required_mb, 1),
                "available_mb": round(exc.available_mb, 1),
            },
        ) from exc
    except ModelLoadError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return LoadResponse(model_id=model_id, status="loaded")
