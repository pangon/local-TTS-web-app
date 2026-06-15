"""Audiobook library API endpoints.

Provides REST endpoints for the library view: listing audiobooks
(REQ-F-library-listing), retrieving a single audiobook with its chapters,
and deleting an audiobook with cascade cleanup of records and audio files
(REQ-F-delete-audiobook).
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, Request, Response
from pydantic import BaseModel

from local_tts.services.library_service import LibraryService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/audiobooks")


class AudiobookSummaryResponse(BaseModel):
    id: str
    title: str
    source_filename: str
    model_id: str
    voice: str | None
    language: str | None
    created_at: str
    chapter_count: int


class ChapterResponse(BaseModel):
    chapter_number: int
    title: str
    duration_seconds: float | None


class AudiobookDetailResponse(BaseModel):
    id: str
    title: str
    source_filename: str
    model_id: str
    voice: str | None
    language: str | None
    created_at: str
    chapters: list[ChapterResponse]


def _get_library_service(request: Request) -> LibraryService:
    """Retrieve the LibraryService from app state."""
    return request.app.state.library_service


@router.get("")
async def list_audiobooks(request: Request) -> list[AudiobookSummaryResponse]:
    """List all audiobooks with chapter counts for the library view."""
    service = _get_library_service(request)
    return [
        AudiobookSummaryResponse(
            id=a.id,
            title=a.title,
            source_filename=a.source_filename,
            model_id=a.model_id,
            voice=a.voice,
            language=a.language,
            created_at=a.created_at,
            chapter_count=a.chapter_count,
        )
        for a in service.list_audiobooks()
    ]


@router.get("/{audiobook_id}")
async def get_audiobook(audiobook_id: str, request: Request) -> AudiobookDetailResponse:
    """Return a single audiobook with its full chapter list."""
    service = _get_library_service(request)
    book = service.get_audiobook(audiobook_id)
    if book is None:
        raise HTTPException(status_code=404, detail="Audiobook not found")

    return AudiobookDetailResponse(
        id=book.id,
        title=book.title,
        source_filename=book.source_filename,
        model_id=book.model_id,
        voice=book.voice,
        language=book.language,
        created_at=book.created_at,
        chapters=[
            ChapterResponse(
                chapter_number=ch.chapter_number,
                title=ch.title,
                duration_seconds=ch.duration_seconds,
            )
            for ch in book.chapters
        ],
    )


@router.delete("/{audiobook_id}", status_code=204)
async def delete_audiobook(audiobook_id: str, request: Request) -> Response:
    """Delete an audiobook, its records, and its audio files.

    Confirmation is handled by the frontend before this endpoint is called
    (REQ-F-delete-audiobook).
    """
    service = _get_library_service(request)
    if not service.delete_audiobook(audiobook_id):
        raise HTTPException(status_code=404, detail="Audiobook not found")

    return Response(status_code=204)
