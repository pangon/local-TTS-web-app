"""Text-preprocessing API endpoint.

Provides the synchronous ``POST /preprocess`` entry point of the
preprocess-then-confirm flow (``DEC-preprocess-review-flow``,
``DEC-text-preprocessing-pipeline``).  It accepts either an uploaded ``.txt``
file (the audiobook path, ``REQ-F-upload-text-file``) or raw ``text`` (the
preview path), runs the modular normalization pipeline using the currently
loaded model's profile, and returns the normalized, TTS-ready text together
with before/after character counts so the user can review exactly what will be
read aloud before generation (``REQ-USA-normalized-text-review``).

The call is synchronous and bounded in latency
(``REQ-PERF-preprocessing-overhead``).  The actual normalization is delegated
to the GPU-agnostic :class:`~local_tts.preprocessing.PreprocessingService`;
this layer owns input validation and the "no model loaded" error so the
service stays decoupled and unit-testable without a GPU.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile
from pydantic import BaseModel

from local_tts.preprocessing import PreprocessingService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/preprocess")

MAX_FILE_SIZE_BYTES = 2 * 1024 * 1024  # 2 MB (REQ-F-upload-text-file)


class PreprocessResponse(BaseModel):
    """Response body for ``POST /preprocess`` (mirrors ``PreprocessResult``)."""

    normalized_text: str
    language: str
    model_id: str | None
    original_char_count: int
    normalized_char_count: int


def _get_preprocessing_service(request: Request) -> PreprocessingService:
    return request.app.state.preprocessing_service


async def _read_uploaded_text(file: UploadFile) -> str:
    """Validate and decode an uploaded ``.txt`` file (REQ-F-upload-text-file).

    Raises a 400 ``HTTPException`` for a non-``.txt`` extension, a file above
    the 2 MB limit, invalid UTF-8, or empty content.
    """
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

    return text


@router.post("")
async def preprocess_text(
    request: Request,
    file: UploadFile | None = File(default=None),
    text: str | None = Form(default=None),
    language: str | None = Form(default=None),
) -> PreprocessResponse:
    """Normalize raw input and return the TTS-ready text for review.

    Accepts exactly one of an uploaded ``.txt`` file or raw ``text`` plus an
    optional output ``language`` (defaults to the configured default language).
    Applies the currently loaded model's preprocessing profile and returns the
    normalized text with before/after char counts
    (``REQ-USA-normalized-text-review``).
    """
    file_provided = file is not None
    text_provided = text is not None and text != ""

    if file_provided and text_provided:
        raise HTTPException(
            status_code=400,
            detail="Provide exactly one of 'file' or 'text', not both",
        )
    if not file_provided and not text_provided:
        raise HTTPException(
            status_code=400,
            detail="Provide either a 'file' upload or 'text' input",
        )

    if file_provided:
        assert file is not None  # narrowed by file_provided
        raw_text = await _read_uploaded_text(file)
    else:
        assert text is not None  # narrowed by text_provided
        raw_text = text
        if not raw_text.strip():
            raise HTTPException(status_code=400, detail="Text input is empty")

    # The pipeline applies the loaded model's profile (DEC-preprocess-review-flow);
    # the API layer owns the "no model loaded" error so the service stays
    # GPU-agnostic.
    tts_engine = request.app.state.tts_engine
    model_id = tts_engine.loaded_model_id
    if model_id is None:
        raise HTTPException(status_code=409, detail="No model loaded")

    service = _get_preprocessing_service(request)
    result = service.preprocess(raw_text, language=language, model_id=model_id)

    logger.info(
        "Preprocessed %d chars -> %d chars (model=%s, language=%s)",
        result.original_char_count,
        result.normalized_char_count,
        result.model_id,
        result.language,
    )

    return PreprocessResponse(
        normalized_text=result.normalized_text,
        language=result.language,
        model_id=result.model_id,
        original_char_count=result.original_char_count,
        normalized_char_count=result.normalized_char_count,
    )
