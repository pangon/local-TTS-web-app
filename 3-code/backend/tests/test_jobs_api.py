"""Tests for synthesis job API endpoint (TASK-synthesis-job-api).

Covers:
- POST /api/v1/jobs/synthesis — create synthesis job from .txt file upload
- File validation: extension, size limit, UTF-8 encoding, empty content
- Model loaded check (409 when no model loaded)
- Disk space preflight check (409 when insufficient)
- Successful job creation returns 201 with correct shape
- Optional voice and language parameters forwarded to JobService
"""

from __future__ import annotations

import io
from pathlib import Path
from unittest.mock import MagicMock, PropertyMock, patch

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


def _txt_file(content: str = "Hello world", filename: str = "book.txt") -> dict:
    """Build a multipart file upload dict for httpx."""
    return {"file": (filename, io.BytesIO(content.encode("utf-8")), "text/plain")}


def _binary_file(content: bytes, filename: str = "book.txt") -> dict:
    """Build a multipart file upload dict with raw bytes."""
    return {"file": (filename, io.BytesIO(content), "application/octet-stream")}


# ---------------------------------------------------------------------------
# Successful creation
# ---------------------------------------------------------------------------


class TestCreateSynthesisJobSuccess:
    @pytest.mark.anyio
    async def test_returns_201_with_job_info(self, test_app):
        app, mock_svc, _ = test_app
        with patch("local_tts.api.jobs.shutil.disk_usage") as mock_disk:
            mock_disk.return_value = MagicMock(free=10 * 1024 * 1024 * 1024)  # 10 GB
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                resp = await client.post(
                    "/api/v1/jobs/synthesis", files=_txt_file("Hello world")
                )

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
                    files=_txt_file("Some text content", "my-book.txt"),
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
                    files=_txt_file("Text"),
                    data={"voice": "af_heart", "language": "en"},
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
                    "/api/v1/jobs/synthesis", files=_txt_file("Hello")
                )

        data = resp.json()
        assert set(data.keys()) == {"id", "type", "status", "progress", "created_at"}


# ---------------------------------------------------------------------------
# File validation (REQ-F-upload-text-file)
# ---------------------------------------------------------------------------


class TestFileValidation:
    @pytest.mark.anyio
    async def test_400_non_txt_extension(self, test_app):
        app, _, _ = test_app
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.post(
                "/api/v1/jobs/synthesis",
                files={"file": ("book.pdf", io.BytesIO(b"content"), "application/pdf")},
            )
        assert resp.status_code == 400
        assert ".txt" in resp.json()["detail"]

    @pytest.mark.anyio
    async def test_400_file_exceeds_2mb(self, test_app):
        app, _, _ = test_app
        large_content = b"x" * (2 * 1024 * 1024 + 1)
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.post(
                "/api/v1/jobs/synthesis",
                files=_binary_file(large_content, "big.txt"),
            )
        assert resp.status_code == 400
        assert "2 MB" in resp.json()["detail"]

    @pytest.mark.anyio
    async def test_400_invalid_utf8(self, test_app):
        app, _, _ = test_app
        invalid_utf8 = b"\xff\xfe" + b"Hello"
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.post(
                "/api/v1/jobs/synthesis",
                files=_binary_file(invalid_utf8, "bad.txt"),
            )
        assert resp.status_code == 400
        assert "UTF-8" in resp.json()["detail"]

    @pytest.mark.anyio
    async def test_400_empty_file(self, test_app):
        app, _, _ = test_app
        with patch("local_tts.api.jobs.shutil.disk_usage") as mock_disk:
            mock_disk.return_value = MagicMock(free=10 * 1024 * 1024 * 1024)
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                resp = await client.post(
                    "/api/v1/jobs/synthesis", files=_txt_file("")
                )
        assert resp.status_code == 400
        assert "empty" in resp.json()["detail"].lower()

    @pytest.mark.anyio
    async def test_400_whitespace_only_file(self, test_app):
        app, _, _ = test_app
        with patch("local_tts.api.jobs.shutil.disk_usage") as mock_disk:
            mock_disk.return_value = MagicMock(free=10 * 1024 * 1024 * 1024)
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                resp = await client.post(
                    "/api/v1/jobs/synthesis", files=_txt_file("   \n\t  ")
                )
        assert resp.status_code == 400
        assert "empty" in resp.json()["detail"].lower()

    @pytest.mark.anyio
    async def test_accepts_exactly_2mb_file(self, test_app):
        app, _, _ = test_app
        content = "a" * (2 * 1024 * 1024)
        with patch("local_tts.api.jobs.shutil.disk_usage") as mock_disk:
            mock_disk.return_value = MagicMock(free=100 * 1024 * 1024 * 1024)
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                resp = await client.post(
                    "/api/v1/jobs/synthesis", files=_txt_file(content)
                )
        assert resp.status_code == 201

    @pytest.mark.anyio
    async def test_accepts_case_insensitive_txt_extension(self, test_app):
        app, _, _ = test_app
        with patch("local_tts.api.jobs.shutil.disk_usage") as mock_disk:
            mock_disk.return_value = MagicMock(free=10 * 1024 * 1024 * 1024)
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                resp = await client.post(
                    "/api/v1/jobs/synthesis",
                    files={"file": ("BOOK.TXT", io.BytesIO(b"Hello"), "text/plain")},
                )
        assert resp.status_code == 201


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
                "/api/v1/jobs/synthesis", files=_txt_file("Hello")
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
                    "/api/v1/jobs/synthesis", files=_txt_file("x" * 10000)
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
                    "/api/v1/jobs/synthesis", files=_txt_file("Hello world")
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
                    "/api/v1/jobs/synthesis", files=_txt_file("Hello")
                )
        mock_disk.assert_called_once_with(Path("/tmp/test-data"))


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
