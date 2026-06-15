"""Playback position API endpoints (REQ-F-playback-resume).

Exposes the two-level resume bookmark for an audiobook:

- ``GET  /audiobooks/{id}/position`` — read the last active chapter and the
  saved per-chapter timestamps.
- ``PUT  /audiobooks/{id}/position`` — save the audiobook-level bookmark and a
  chapter's timestamp (called by the frontend on pause, stop, or chapter
  change).

Paths sit under ``/audiobooks`` (matching api-design.md) but are backed by the
dedicated :class:`PlaybackService` rather than the LibraryService.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from local_tts.services.playback_service import PlaybackService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/audiobooks")


class PlaybackPositionResponse(BaseModel):
    last_chapter_number: int
    chapters: dict[str, float]


class UpdatePositionRequest(BaseModel):
    chapter_number: int = Field(ge=1)
    position_seconds: float = Field(ge=0)


class UpdatePositionResponse(BaseModel):
    chapter_number: int
    position_seconds: float


def _get_playback_service(request: Request) -> PlaybackService:
    """Retrieve the PlaybackService from app state."""
    return request.app.state.playback_service


@router.get("/{audiobook_id}/position")
async def get_playback_position(
    audiobook_id: str, request: Request
) -> PlaybackPositionResponse:
    """Return the two-level playback bookmark for an audiobook.

    Returns ``{"last_chapter_number": 1, "chapters": {}}`` if the audiobook
    exists but has never been played (REQ-F-playback-resume).
    """
    service = _get_playback_service(request)
    position = service.get_position(audiobook_id)
    if position is None:
        raise HTTPException(status_code=404, detail="Audiobook not found")

    return PlaybackPositionResponse(
        last_chapter_number=position.last_chapter_number,
        chapters=position.chapters,
    )


@router.put("/{audiobook_id}/position")
async def update_playback_position(
    audiobook_id: str, body: UpdatePositionRequest, request: Request
) -> UpdatePositionResponse:
    """Save the audiobook-level bookmark and the per-chapter timestamp.

    Invalid chapter numbers or positions are rejected by request validation
    (422); an unknown audiobook returns 404 (REQ-F-playback-resume).
    """
    service = _get_playback_service(request)
    updated = service.update_position(
        audiobook_id, body.chapter_number, body.position_seconds
    )
    if not updated:
        raise HTTPException(status_code=404, detail="Audiobook not found")

    return UpdatePositionResponse(
        chapter_number=body.chapter_number,
        position_seconds=body.position_seconds,
    )
