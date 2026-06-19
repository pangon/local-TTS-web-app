"""Tests for the text-preprocessing API endpoint (TASK-preprocess-api).

Covers POST /api/v1/preprocess:
- File input and raw-text input both normalized via the real pipeline
- Input validation (400): exactly-one-of file/text, .txt extension, 2 MB
  limit, UTF-8 decoding, empty/whitespace input (REQ-F-upload-text-file)
- Model-loaded check (409 when no model is loaded)
- Response shape and before/after char counts (REQ-USA-normalized-text-review)
- Latency bounds for the preprocessing pipeline (REQ-PERF-preprocessing-overhead)

The tests wire in the *real* PreprocessingService (it has no GPU dependency)
so the endpoint exercises the actual normalization pipeline; only the TTS
engine (for the loaded-model id) is mocked.
"""

from __future__ import annotations

import io
import time
from unittest.mock import MagicMock

import pytest
from httpx import ASGITransport, AsyncClient

from local_tts.preprocessing import PreprocessingService

LOADED_MODEL_ID = "hexgrad/Kokoro-82M"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _create_test_app() -> tuple:
    """Create a minimal FastAPI app with the preprocess route for testing."""
    from fastapi import FastAPI

    from local_tts.api.preprocess import router

    app = FastAPI()
    app.include_router(router, prefix="/api/v1")

    mock_tts_engine = MagicMock()
    mock_tts_engine.loaded_model_id = LOADED_MODEL_ID

    app.state.tts_engine = mock_tts_engine
    app.state.preprocessing_service = PreprocessingService()

    return app, mock_tts_engine


@pytest.fixture()
def test_app():
    return _create_test_app()


def _client(app) -> AsyncClient:
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


def _txt_file(content: str = "Hello world", filename: str = "book.txt") -> dict:
    """Build a multipart .txt file upload dict for httpx."""
    return {"file": (filename, io.BytesIO(content.encode("utf-8")), "text/plain")}


def _binary_file(content: bytes, filename: str = "book.txt") -> dict:
    return {"file": (filename, io.BytesIO(content), "application/octet-stream")}


# ---------------------------------------------------------------------------
# Successful preprocessing
# ---------------------------------------------------------------------------


class TestPreprocessSuccess:
    @pytest.mark.anyio
    async def test_text_input_returns_200_with_expected_shape(self, test_app):
        app, _ = test_app
        async with _client(app) as client:
            resp = await client.post(
                "/api/v1/preprocess", data={"text": "Ciao mondo."}
            )

        assert resp.status_code == 200
        data = resp.json()
        assert set(data.keys()) == {
            "normalized_text",
            "language",
            "model_id",
            "original_char_count",
            "normalized_char_count",
        }
        assert data["model_id"] == LOADED_MODEL_ID
        assert data["language"] == "it"  # default language (DEC-default-italian-language)
        assert isinstance(data["normalized_text"], str)

    @pytest.mark.anyio
    async def test_file_input_returns_200(self, test_app):
        app, _ = test_app
        async with _client(app) as client:
            resp = await client.post(
                "/api/v1/preprocess", files=_txt_file("Capitolo uno. Ciao.")
            )

        assert resp.status_code == 200
        assert resp.json()["model_id"] == LOADED_MODEL_ID

    @pytest.mark.anyio
    async def test_char_counts_reflect_input_and_output(self, test_app):
        app, _ = test_app
        raw = "Ciao   mondo."  # whitespace collapse shrinks the text
        async with _client(app) as client:
            resp = await client.post("/api/v1/preprocess", data={"text": raw})

        data = resp.json()
        assert data["original_char_count"] == len(raw)
        assert data["normalized_char_count"] == len(data["normalized_text"])

    @pytest.mark.anyio
    async def test_supported_language_is_forwarded_to_pipeline(self, test_app):
        app, _ = test_app
        async with _client(app) as client:
            resp = await client.post(
                "/api/v1/preprocess",
                data={"text": "Ciao mondo.", "language": "it"},
            )

        assert resp.status_code == 200
        assert resp.json()["language"] == "it"


class TestNormalizationApplied:
    """The endpoint must apply the loaded model's profile so the reviewed text
    shows how numbers/symbols are verbalized (REQ-USA-normalized-text-review)."""

    @pytest.mark.anyio
    async def test_percentage_is_verbalized_in_italian(self, test_app):
        app, _ = test_app
        async with _client(app) as client:
            resp = await client.post(
                "/api/v1/preprocess", data={"text": "Sconto del 25%."}
            )

        normalized = resp.json()["normalized_text"]
        assert "per cento" in normalized
        assert "%" not in normalized

    @pytest.mark.anyio
    async def test_file_path_runs_full_pipeline(self, test_app):
        app, _ = test_app
        async with _client(app) as client:
            resp = await client.post(
                "/api/v1/preprocess",
                files=_txt_file("Costo: 10 €."),
            )

        normalized = resp.json()["normalized_text"]
        assert "euro" in normalized
        assert "€" not in normalized


# ---------------------------------------------------------------------------
# Input validation (REQ-F-upload-text-file)
# ---------------------------------------------------------------------------


class TestInputValidation:
    @pytest.mark.anyio
    async def test_400_when_neither_file_nor_text(self, test_app):
        app, _ = test_app
        async with _client(app) as client:
            resp = await client.post("/api/v1/preprocess", data={"language": "it"})
        assert resp.status_code == 400
        assert "either" in resp.json()["detail"].lower()

    @pytest.mark.anyio
    async def test_400_when_both_file_and_text(self, test_app):
        app, _ = test_app
        async with _client(app) as client:
            resp = await client.post(
                "/api/v1/preprocess",
                files=_txt_file("from file"),
                data={"text": "from text"},
            )
        assert resp.status_code == 400
        assert "not both" in resp.json()["detail"].lower()

    @pytest.mark.anyio
    async def test_400_non_txt_extension(self, test_app):
        app, _ = test_app
        async with _client(app) as client:
            resp = await client.post(
                "/api/v1/preprocess",
                files={"file": ("book.pdf", io.BytesIO(b"content"), "application/pdf")},
            )
        assert resp.status_code == 400
        assert ".txt" in resp.json()["detail"]

    @pytest.mark.anyio
    async def test_400_file_exceeds_2mb(self, test_app):
        app, _ = test_app
        large = b"x" * (2 * 1024 * 1024 + 1)
        async with _client(app) as client:
            resp = await client.post(
                "/api/v1/preprocess", files=_binary_file(large, "big.txt")
            )
        assert resp.status_code == 400
        assert "2 MB" in resp.json()["detail"]

    @pytest.mark.anyio
    async def test_400_invalid_utf8(self, test_app):
        app, _ = test_app
        invalid = b"\xff\xfe" + b"Hello"
        async with _client(app) as client:
            resp = await client.post(
                "/api/v1/preprocess", files=_binary_file(invalid, "bad.txt")
            )
        assert resp.status_code == 400
        assert "UTF-8" in resp.json()["detail"]

    @pytest.mark.anyio
    async def test_400_empty_file(self, test_app):
        app, _ = test_app
        async with _client(app) as client:
            resp = await client.post("/api/v1/preprocess", files=_txt_file(""))
        # An empty file body is an absent form field → treated as "neither input".
        assert resp.status_code == 400

    @pytest.mark.anyio
    async def test_400_whitespace_only_file(self, test_app):
        app, _ = test_app
        async with _client(app) as client:
            resp = await client.post(
                "/api/v1/preprocess", files=_txt_file("   \n\t  ")
            )
        assert resp.status_code == 400
        assert "empty" in resp.json()["detail"].lower()

    @pytest.mark.anyio
    async def test_400_whitespace_only_text(self, test_app):
        app, _ = test_app
        async with _client(app) as client:
            resp = await client.post(
                "/api/v1/preprocess", data={"text": "   \n\t  "}
            )
        assert resp.status_code == 400
        assert "empty" in resp.json()["detail"].lower()

    @pytest.mark.anyio
    async def test_accepts_exactly_2mb_file(self, test_app):
        app, _ = test_app
        content = "a" * (2 * 1024 * 1024)
        async with _client(app) as client:
            resp = await client.post("/api/v1/preprocess", files=_txt_file(content))
        assert resp.status_code == 200

    @pytest.mark.anyio
    async def test_accepts_case_insensitive_txt_extension(self, test_app):
        app, _ = test_app
        async with _client(app) as client:
            resp = await client.post(
                "/api/v1/preprocess",
                files={"file": ("BOOK.TXT", io.BytesIO(b"Ciao"), "text/plain")},
            )
        assert resp.status_code == 200


# ---------------------------------------------------------------------------
# Model-loaded check
# ---------------------------------------------------------------------------


class TestModelLoadedCheck:
    @pytest.mark.anyio
    async def test_409_no_model_loaded_with_text(self, test_app):
        app, mock_engine = test_app
        mock_engine.loaded_model_id = None
        async with _client(app) as client:
            resp = await client.post(
                "/api/v1/preprocess", data={"text": "Ciao mondo."}
            )
        assert resp.status_code == 409
        assert resp.json()["detail"] == "No model loaded"

    @pytest.mark.anyio
    async def test_409_no_model_loaded_with_file(self, test_app):
        app, mock_engine = test_app
        mock_engine.loaded_model_id = None
        async with _client(app) as client:
            resp = await client.post(
                "/api/v1/preprocess", files=_txt_file("Ciao mondo.")
            )
        assert resp.status_code == 409
        assert resp.json()["detail"] == "No model loaded"

    @pytest.mark.anyio
    async def test_input_validation_precedes_model_check(self, test_app):
        """A malformed request is rejected (400) even when no model is loaded,
        matching the synthesis endpoint's validate-then-check ordering."""
        app, mock_engine = test_app
        mock_engine.loaded_model_id = None
        async with _client(app) as client:
            resp = await client.post(
                "/api/v1/preprocess",
                files={"file": ("book.pdf", io.BytesIO(b"x"), "application/pdf")},
            )
        assert resp.status_code == 400

    @pytest.mark.anyio
    async def test_unsupported_language_returns_400(self, test_app):
        """An output language with no registered data is rejected (400)
        rather than silently passing the text through unchanged."""
        app, _ = test_app
        async with _client(app) as client:
            resp = await client.post(
                "/api/v1/preprocess",
                data={"text": "Hello world.", "language": "en"},
            )
        assert resp.status_code == 400
        assert "Unsupported output language" in resp.json()["detail"]

    @pytest.mark.anyio
    async def test_unsupported_language_precedes_model_check(self, test_app):
        """Language validation is an input check, so it returns 400 even when
        no model is loaded (matching the validate-then-check ordering)."""
        app, mock_engine = test_app
        mock_engine.loaded_model_id = None
        async with _client(app) as client:
            resp = await client.post(
                "/api/v1/preprocess",
                data={"text": "Hello world.", "language": "en"},
            )
        assert resp.status_code == 400


# ---------------------------------------------------------------------------
# Latency bounds (REQ-PERF-preprocessing-overhead)
# ---------------------------------------------------------------------------


class TestLatencyBounds:
    """Smoke guards for the preprocessing latency bounds. The bounds in
    REQ-PERF-preprocessing-overhead (≤1 s for ≤500 chars, ≤10 s for ~2 MB) are
    specified on min-spec hardware and are generous enough that even slow CI
    stays well within them; these assert the pipeline does not regress into
    super-linear behavior."""

    def test_preview_input_under_one_second(self):
        service = PreprocessingService()
        text = (
            "Il prezzo era 1.234,56 € il 15/03/2026, con uno sconto del 25%. "
        ) * 7  # ~ 450 chars, mixed numbers/dates/currency/percent
        text = text[:500]

        start = time.perf_counter()
        service.preprocess(text, language="it", model_id=LOADED_MODEL_ID)
        elapsed = time.perf_counter() - start

        assert elapsed <= 1.0, f"500-char preprocessing took {elapsed:.3f}s (> 1s)"

    def test_large_document_under_ten_seconds(self):
        service = PreprocessingService()
        paragraph = (
            "Nel capitolo seguente si descrive un esempio. "
            "Il valore era 42 e la temperatura 20°C. "
            "Vedi pag. 12 per i dettagli, ecc.\n\n"
        )
        # Build a ~2 MB document.
        text = paragraph * (2 * 1024 * 1024 // len(paragraph) + 1)
        text = text[: 2 * 1024 * 1024]

        start = time.perf_counter()
        service.preprocess(text, language="it", model_id=LOADED_MODEL_ID)
        elapsed = time.perf_counter() - start

        assert elapsed <= 10.0, f"~2MB preprocessing took {elapsed:.3f}s (> 10s)"


# ---------------------------------------------------------------------------
# Route registration
# ---------------------------------------------------------------------------


class TestRoutes:
    def test_preprocess_route_registered(self):
        from fastapi import FastAPI

        from local_tts.api.preprocess import router

        app = FastAPI()
        app.include_router(router, prefix="/api/v1")
        paths = [route.path for route in app.routes]
        assert "/api/v1/preprocess" in paths

    def test_route_included_in_main_router(self):
        from local_tts.api.router import api_router

        paths = [route.path for route in api_router.routes]
        assert "/preprocess" in paths
