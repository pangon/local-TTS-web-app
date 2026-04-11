"""Tests for model management API endpoints (TASK-model-service).

Covers:
- GET /api/v1/models — list models with cache/load status
- POST /api/v1/models/{model_id}/download — start async download
- POST /api/v1/models/{model_id}/load — synchronous GPU load
- Error responses: 404, 409 (already cached, insufficient disk, insufficient VRAM)
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from httpx import ASGITransport, AsyncClient

from local_tts.api.sse import EventBus
from local_tts.services.model_service import InsufficientVRAMError, ModelService
from local_tts.tts.model_loader import DiskSpaceCheck, ModelInfo, ModelLoadError


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _create_test_app() -> tuple:
    """Create a minimal FastAPI app with model routes for testing."""
    from fastapi import FastAPI

    from local_tts.api.models import router

    app = FastAPI()
    app.include_router(router, prefix="/api/v1")

    mock_service = MagicMock(spec=ModelService)
    mock_service.list_models.return_value = [
        ModelInfo("facebook/mms-tts-eng", "MMS TTS English", is_cached=True, is_loaded=True, loader_available=True),
        ModelInfo("facebook/mms-tts-ita", "MMS TTS Italian", is_cached=False, is_loaded=False, loader_available=False),
    ]
    mock_service.is_model_cached.return_value = False
    mock_service.is_downloading.return_value = False
    mock_service.check_disk_space.return_value = DiskSpaceCheck(
        sufficient=True, estimated_mb=100.0, available_mb=500.0
    )
    app.state.model_service = mock_service

    return app, mock_service


@pytest.fixture()
def test_app():
    app, mock_service = _create_test_app()
    return app, mock_service


# ---------------------------------------------------------------------------
# GET /api/v1/models
# ---------------------------------------------------------------------------

class TestListModelsEndpoint:
    @pytest.mark.anyio
    async def test_returns_model_list(self, test_app):
        app, _ = test_app
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/api/v1/models")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 2
        assert data[0]["model_id"] == "facebook/mms-tts-eng"
        assert data[0]["is_cached"] is True
        assert data[0]["is_loaded"] is True
        assert data[1]["model_id"] == "facebook/mms-tts-ita"
        assert data[1]["is_cached"] is False

    @pytest.mark.anyio
    async def test_response_fields(self, test_app):
        app, _ = test_app
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/api/v1/models")
        model = resp.json()[0]
        assert set(model.keys()) == {"model_id", "name", "is_cached", "is_loaded", "loader_available"}

    @pytest.mark.anyio
    async def test_loader_available_reflected_in_response(self, test_app):
        app, _ = test_app
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/api/v1/models")
        data = resp.json()
        assert data[0]["loader_available"] is True
        assert data[1]["loader_available"] is False


# ---------------------------------------------------------------------------
# POST /api/v1/models/{model_id}/download
# ---------------------------------------------------------------------------

class TestDownloadModelEndpoint:
    @pytest.mark.anyio
    async def test_returns_202_on_success(self, test_app):
        app, mock_service = test_app
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post("/api/v1/models/facebook/mms-tts-eng/download")
        assert resp.status_code == 202
        data = resp.json()
        assert data["model_id"] == "facebook/mms-tts-eng"
        assert data["status"] == "downloading"
        mock_service.start_download.assert_called_once()

    @pytest.mark.anyio
    async def test_409_when_already_cached(self, test_app):
        app, mock_service = test_app
        mock_service.is_model_cached.return_value = True
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post("/api/v1/models/facebook/mms-tts-eng/download")
        assert resp.status_code == 409
        assert "already cached" in resp.json()["detail"]

    @pytest.mark.anyio
    async def test_409_when_download_in_progress(self, test_app):
        app, mock_service = test_app
        mock_service.is_downloading.return_value = True
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post("/api/v1/models/facebook/mms-tts-eng/download")
        assert resp.status_code == 409
        assert "already in progress" in resp.json()["detail"]

    @pytest.mark.anyio
    async def test_409_when_insufficient_disk_space(self, test_app):
        app, mock_service = test_app
        mock_service.check_disk_space.return_value = DiskSpaceCheck(
            sufficient=False, estimated_mb=2048.0, available_mb=500.0
        )
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post("/api/v1/models/facebook/mms-tts-eng/download")
        assert resp.status_code == 409
        detail = resp.json()["detail"]
        assert detail["detail"] == "Insufficient disk space"
        assert detail["estimated_mb"] == 2048.0
        assert detail["available_mb"] == 500.0


# ---------------------------------------------------------------------------
# POST /api/v1/models/{model_id}/load
# ---------------------------------------------------------------------------

class TestLoadModelEndpoint:
    @pytest.mark.anyio
    async def test_returns_200_on_success(self, test_app):
        app, mock_service = test_app
        mock_service.is_model_cached.return_value = True
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post("/api/v1/models/facebook/mms-tts-eng/load")
        assert resp.status_code == 200
        data = resp.json()
        assert data["model_id"] == "facebook/mms-tts-eng"
        assert data["status"] == "loaded"
        mock_service.load_model.assert_called_once_with("facebook/mms-tts-eng")

    @pytest.mark.anyio
    async def test_404_when_not_cached(self, test_app):
        app, mock_service = test_app
        mock_service.is_model_cached.return_value = False
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post("/api/v1/models/facebook/mms-tts-eng/load")
        assert resp.status_code == 404
        assert "not cached" in resp.json()["detail"]

    @pytest.mark.anyio
    async def test_409_on_insufficient_vram(self, test_app):
        app, mock_service = test_app
        mock_service.is_model_cached.return_value = True
        mock_service.load_model.side_effect = InsufficientVRAMError(
            required_mb=4096.0, available_mb=2048.0
        )
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post("/api/v1/models/facebook/mms-tts-eng/load")
        assert resp.status_code == 409
        detail = resp.json()["detail"]
        assert detail["detail"] == "Insufficient VRAM"
        assert detail["required_mb"] == 4096.0
        assert detail["available_mb"] == 2048.0

    @pytest.mark.anyio
    async def test_500_on_generic_load_error(self, test_app):
        app, mock_service = test_app
        mock_service.is_model_cached.return_value = True
        mock_service.load_model.side_effect = ModelLoadError("CUDA OOM")
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post("/api/v1/models/facebook/mms-tts-eng/load")
        assert resp.status_code == 500


# ---------------------------------------------------------------------------
# Route registration
# ---------------------------------------------------------------------------

class TestModelRoutes:
    def test_model_routes_registered(self):
        from fastapi import FastAPI

        from local_tts.api.models import router

        app = FastAPI()
        app.include_router(router, prefix="/api/v1")
        paths = [route.path for route in app.routes]
        assert "/api/v1/models" in paths
        assert "/api/v1/models/{model_id:path}/download" in paths
        assert "/api/v1/models/{model_id:path}/load" in paths
