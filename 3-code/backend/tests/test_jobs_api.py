"""Tests for synthesis job API endpoint (TASK-synthesis-api-text-input).

Covers the JSON contract of ``POST /api/v1/jobs/synthesis`` introduced by the
preprocess-then-confirm flow (DEC-preprocess-review-flow), which supersedes the
multipart file-upload contract of TASK-synthesis-job-api (file upload and text
validation now live at ``POST /preprocess`` / ``tests/test_preprocess_api.py``):

- POST /api/v1/jobs/synthesis — create synthesis job from confirmed JSON text
- Input validation: empty / whitespace-only text (400); missing required
  fields (422 via FastAPI)
- Synthesizes exactly the confirmed text — no re-preprocessing
  (REQ-USA-normalized-text-review)
- Model loaded check (409 when no model loaded)
- Disk space preflight check derived from text length (409 when insufficient)
- Successful job creation returns 201 with correct shape
- Optional voice and language parameters forwarded to JobService
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from local_tts.services.job_service import JobInfo, JobService


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _create_test_app() -> tuple:
    """Create a minimal FastAPI app with jobs routes for testing."""
    from fastapi import FastAPI

    from local_tts.api.jobs import router

    app = FastAPI()
    app.include_router(router, prefix="/api/v1")

    mock_job_service = MagicMock(spec=JobService)
    mock_job_service._data_dir = Path("/tmp/test-data")
    mock_job_service.create_synthesis_job.return_value = JobInfo(
        id="test-job-id",
        audiobook_id=None,
        type="synthesis",
        status="queued",
        progress=0,
        error_message=None,
        created_at="2026-04-12T10:00:00Z",
        started_at=None,
        completed_at=None,
    )

    mock_tts_engine = MagicMock()
    mock_tts_engine.loaded_model_id = "hexgrad/Kokoro-82M"

    app.state.job_service = mock_job_service
    app.state.tts_engine = mock_tts_engine

    return app, mock_job_service, mock_tts_engine


@pytest.fixture()
def test_app():
    app, mock_job_service, mock_tts_engine = _create_test_app()
    return app, mock_job_service, mock_tts_engine


def _body(
    text: str = "Hello world",
    source_filename: str = "book.txt",
    **extra: object,
) -> dict:
    """Build a JSON request body for the synthesis endpoint."""
    payload: dict = {"text": text, "source_filename": source_filename}
    payload.update(extra)
    return payload


# ---------------------------------------------------------------------------
# Successful creation
# ---------------------------------------------------------------------------


class TestCreateSynthesisJobSuccess:
    @pytest.mark.anyio
    async def test_returns_201_with_job_info(self, test_app):
        app, _, _ = test_app
        with patch("local_tts.api.jobs.shutil.disk_usage") as mock_disk:
            mock_disk.return_value = MagicMock(free=10 * 1024 * 1024 * 1024)  # 10 GB
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                resp = await client.post("/api/v1/jobs/synthesis", json=_body())

        assert resp.status_code == 201
        data = resp.json()
        assert data["id"] == "test-job-id"
        assert data["type"] == "synthesis"
        assert data["status"] == "queued"
        assert data["progress"] == 0
        assert "created_at" in data

    @pytest.mark.anyio
    async def test_calls_job_service_with_text_content(self, test_app):
        app, mock_svc, _ = test_app
        with patch("local_tts.api.jobs.shutil.disk_usage") as mock_disk:
            mock_disk.return_value = MagicMock(free=10 * 1024 * 1024 * 1024)
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                await client.post(
                    "/api/v1/jobs/synthesis",
                    json=_body("Some text content", "my-book.txt"),
                )

        mock_svc.create_synthesis_job.assert_called_once_with(
            source_filename="my-book.txt",
            text="Some text content",
            voice=None,
            language=None,
        )

    @pytest.mark.anyio
    async def test_forwards_voice_and_language(self, test_app):
        app, mock_svc, _ = test_app
        with patch("local_tts.api.jobs.shutil.disk_usage") as mock_disk:
            mock_disk.return_value = MagicMock(free=10 * 1024 * 1024 * 1024)
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                await client.post(
                    "/api/v1/jobs/synthesis",
                    json=_body("Text", voice="af_heart", language="en"),
                )

        mock_svc.create_synthesis_job.assert_called_once_with(
            source_filename="book.txt",
            text="Text",
            voice="af_heart",
            language="en",
        )

    @pytest.mark.anyio
    async def test_response_fields_match_api_design(self, test_app):
        app, _, _ = test_app
        with patch("local_tts.api.jobs.shutil.disk_usage") as mock_disk:
            mock_disk.return_value = MagicMock(free=10 * 1024 * 1024 * 1024)
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                resp = await client.post(
                    "/api/v1/jobs/synthesis", json=_body("Hello")
                )

        data = resp.json()
        assert set(data.keys()) == {"id", "type", "status", "progress", "created_at"}


# ---------------------------------------------------------------------------
# Synthesize exactly the confirmed text — no re-preprocessing
# (REQ-USA-normalized-text-review, DEC-preprocess-review-flow)
# ---------------------------------------------------------------------------


class TestSynthesizesExactConfirmedText:
    @pytest.mark.anyio
    async def test_text_passed_through_verbatim(self, test_app):
        app, mock_svc, _ = test_app
        # Text that already went through preprocessing: numbers verbalized,
        # symbols expanded. The endpoint must forward it byte-for-byte and must
        # NOT re-normalize it (e.g. it must not turn "venticinque" back, nor
        # touch the already-spelled-out "per cento").
        confirmed = "Capitolo primo. Erano le venticinque per cento delle voci."
        with patch("local_tts.api.jobs.shutil.disk_usage") as mock_disk:
            mock_disk.return_value = MagicMock(free=10 * 1024 * 1024 * 1024)
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                await client.post(
                    "/api/v1/jobs/synthesis", json=_body(confirmed, "doc.txt")
                )

        _, kwargs = mock_svc.create_synthesis_job.call_args
        assert kwargs["text"] == confirmed

    @pytest.mark.anyio
    async def test_no_preprocessing_service_invoked(self, test_app):
        app, _, _ = test_app
        # The endpoint must not depend on a preprocessing service at all.
        app.state.preprocessing_service = MagicMock()
        with patch("local_tts.api.jobs.shutil.disk_usage") as mock_disk:
            mock_disk.return_value = MagicMock(free=10 * 1024 * 1024 * 1024)
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                await client.post(
                    "/api/v1/jobs/synthesis", json=_body("Già normalizzato.")
                )

        app.state.preprocessing_service.preprocess.assert_not_called()


# ---------------------------------------------------------------------------
# Input validation
# ---------------------------------------------------------------------------


class TestInputValidation:
    @pytest.mark.anyio
    async def test_400_empty_text(self, test_app):
        app, _, _ = test_app
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.post("/api/v1/jobs/synthesis", json=_body(""))
        assert resp.status_code == 400
        assert "empty" in resp.json()["detail"].lower()

    @pytest.mark.anyio
    async def test_400_whitespace_only_text(self, test_app):
        app, _, _ = test_app
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.post(
                "/api/v1/jobs/synthesis", json=_body("   \n\t  ")
            )
        assert resp.status_code == 400
        assert "empty" in resp.json()["detail"].lower()

    @pytest.mark.anyio
    async def test_422_missing_text_field(self, test_app):
        app, _, _ = test_app
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.post(
                "/api/v1/jobs/synthesis", json={"source_filename": "book.txt"}
            )
        assert resp.status_code == 422

    @pytest.mark.anyio
    async def test_422_missing_source_filename_field(self, test_app):
        app, _, _ = test_app
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.post(
                "/api/v1/jobs/synthesis", json={"text": "Hello"}
            )
        assert resp.status_code == 422

    @pytest.mark.anyio
    async def test_empty_text_check_precedes_model_check(self, test_app):
        """Validation runs before the model-loaded check (400, not 409)."""
        app, _, mock_engine = test_app
        mock_engine.loaded_model_id = None
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.post("/api/v1/jobs/synthesis", json=_body(""))
        assert resp.status_code == 400


# ---------------------------------------------------------------------------
# Model loaded check
# ---------------------------------------------------------------------------


class TestModelLoadedCheck:
    @pytest.mark.anyio
    async def test_409_no_model_loaded(self, test_app):
        app, _, mock_engine = test_app
        mock_engine.loaded_model_id = None
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.post(
                "/api/v1/jobs/synthesis", json=_body("Hello")
            )
        assert resp.status_code == 409
        assert "No model loaded" in resp.json()["detail"]


# ---------------------------------------------------------------------------
# Disk space preflight (REQ-F-disk-space-preflight)
# ---------------------------------------------------------------------------


class TestDiskSpacePreflight:
    @pytest.mark.anyio
    async def test_409_insufficient_disk_space(self, test_app):
        app, _, _ = test_app
        with patch("local_tts.api.jobs.shutil.disk_usage") as mock_disk:
            # Simulate very little free space (1 MB)
            mock_disk.return_value = MagicMock(free=1 * 1024 * 1024)
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                # 10,000 chars → estimated ~20 MB, available ~1 MB
                resp = await client.post(
                    "/api/v1/jobs/synthesis", json=_body("x" * 10000)
                )

        assert resp.status_code == 409
        detail = resp.json()["detail"]
        assert detail["detail"] == "Insufficient disk space"
        assert "estimated_mb" in detail
        assert "available_mb" in detail
        assert detail["estimated_mb"] > detail["available_mb"]

    @pytest.mark.anyio
    async def test_passes_with_sufficient_space(self, test_app):
        app, _, _ = test_app
        with patch("local_tts.api.jobs.shutil.disk_usage") as mock_disk:
            mock_disk.return_value = MagicMock(free=50 * 1024 * 1024 * 1024)  # 50 GB
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                resp = await client.post(
                    "/api/v1/jobs/synthesis", json=_body("Hello world")
                )
        assert resp.status_code == 201

    @pytest.mark.anyio
    async def test_disk_check_uses_data_dir(self, test_app):
        app, _, _ = test_app
        with patch("local_tts.api.jobs.shutil.disk_usage") as mock_disk:
            mock_disk.return_value = MagicMock(free=50 * 1024 * 1024 * 1024)
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                await client.post(
                    "/api/v1/jobs/synthesis", json=_body("Hello")
                )
        mock_disk.assert_called_once_with(Path("/tmp/test-data"))

    @pytest.mark.anyio
    async def test_estimate_derived_from_text_length(self, test_app):
        """Disk preflight scales the estimate with the confirmed text length."""
        app, _, _ = test_app
        # ~1.5 MB free; 10,000-char text estimates ~20 MB → fails.
        with patch("local_tts.api.jobs.shutil.disk_usage") as mock_disk:
            mock_disk.return_value = MagicMock(free=int(1.5 * 1024 * 1024))
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                long_resp = await client.post(
                    "/api/v1/jobs/synthesis", json=_body("y" * 10000)
                )
                short_resp = await client.post(
                    "/api/v1/jobs/synthesis", json=_body("short")
                )
        assert long_resp.status_code == 409
        assert short_resp.status_code == 201


# ---------------------------------------------------------------------------
# Disk space estimation
# ---------------------------------------------------------------------------


class TestDiskSpaceEstimation:
    def test_estimate_scales_with_text_length(self):
        from local_tts.api.jobs import _estimate_audio_mb

        small = _estimate_audio_mb(100)
        large = _estimate_audio_mb(10000)
        assert large > small

    def test_estimate_has_minimum(self):
        from local_tts.api.jobs import _estimate_audio_mb

        assert _estimate_audio_mb(1) >= 1.0

    def test_estimate_is_positive(self):
        from local_tts.api.jobs import _estimate_audio_mb

        assert _estimate_audio_mb(0) >= 1.0


# ---------------------------------------------------------------------------
# Route registration
# ---------------------------------------------------------------------------


class TestJobRoutes:
    def test_synthesis_route_registered(self):
        from fastapi import FastAPI

        from local_tts.api.jobs import router

        app = FastAPI()
        app.include_router(router, prefix="/api/v1")
        paths = [route.path for route in app.routes]
        assert "/api/v1/jobs/synthesis" in paths

    def test_route_included_in_main_router(self):
        from local_tts.api.router import api_router

        paths = [route.path for route in api_router.routes]
        assert "/jobs/synthesis" in paths
