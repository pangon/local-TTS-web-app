"""Tests for the ModelService application service (TASK-model-service).

Covers:
- Model listing delegation to TTSEngine
- Disk space checking delegation
- Cache status checking
- Download tracking (in-progress state)
- Background download with SSE event publishing
- Model loading with structured VRAM error reporting
"""

from __future__ import annotations

import asyncio
import threading
from unittest.mock import MagicMock, patch

import pytest

from local_tts.api.sse import EventBus
from local_tts.services.model_service import InsufficientVRAMError, ModelService
from local_tts.tts.model_loader import DiskSpaceCheck, ModelInfo, ModelLoadError


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def mock_tts_engine() -> MagicMock:
    engine = MagicMock()
    engine.list_models.return_value = [
        ModelInfo("facebook/mms-tts-eng", "MMS TTS English", is_cached=True, is_loaded=False),
        ModelInfo("facebook/mms-tts-ita", "MMS TTS Italian", is_cached=False, is_loaded=False),
    ]
    engine.is_model_cached.return_value = False
    engine.check_disk_space.return_value = DiskSpaceCheck(
        sufficient=True, estimated_mb=100.0, available_mb=500.0
    )
    engine.loaded_model_id = None
    return engine


@pytest.fixture()
def event_bus() -> EventBus:
    return EventBus()


@pytest.fixture()
def service(mock_tts_engine: MagicMock, event_bus: EventBus) -> ModelService:
    return ModelService(mock_tts_engine, event_bus)


# ---------------------------------------------------------------------------
# list_models
# ---------------------------------------------------------------------------

class TestListModels:
    def test_delegates_to_tts_engine(self, service: ModelService, mock_tts_engine: MagicMock):
        result = service.list_models()
        mock_tts_engine.list_models.assert_called_once()
        assert len(result) == 2
        assert result[0].model_id == "facebook/mms-tts-eng"

    def test_returns_model_info_objects(self, service: ModelService):
        result = service.list_models()
        assert all(isinstance(m, ModelInfo) for m in result)


# ---------------------------------------------------------------------------
# check_disk_space
# ---------------------------------------------------------------------------

class TestCheckDiskSpace:
    def test_delegates_to_tts_engine(self, service: ModelService, mock_tts_engine: MagicMock):
        result = service.check_disk_space("facebook/mms-tts-eng")
        mock_tts_engine.check_disk_space.assert_called_once_with("facebook/mms-tts-eng")
        assert result.sufficient is True


# ---------------------------------------------------------------------------
# is_model_cached
# ---------------------------------------------------------------------------

class TestIsModelCached:
    def test_delegates_to_tts_engine(self, service: ModelService, mock_tts_engine: MagicMock):
        mock_tts_engine.is_model_cached.return_value = True
        assert service.is_model_cached("facebook/mms-tts-eng") is True
        mock_tts_engine.is_model_cached.assert_called_once_with("facebook/mms-tts-eng")


# ---------------------------------------------------------------------------
# download tracking
# ---------------------------------------------------------------------------

class TestDownloadTracking:
    def test_not_downloading_initially(self, service: ModelService):
        assert service.is_downloading("facebook/mms-tts-eng") is False

    @pytest.mark.anyio
    async def test_tracks_active_download(self, service: ModelService, mock_tts_engine: MagicMock):
        """Download is tracked while in progress."""
        download_started = threading.Event()
        download_proceed = threading.Event()

        def slow_download(model_id, progress_callback=None):
            download_started.set()
            download_proceed.wait(timeout=5)

        mock_tts_engine.download_model.side_effect = slow_download

        loop = asyncio.get_running_loop()
        service.start_download("facebook/mms-tts-eng", loop)

        download_started.wait(timeout=5)
        assert service.is_downloading("facebook/mms-tts-eng") is True

        download_proceed.set()
        # Wait for background thread to finish
        await asyncio.sleep(0.1)
        assert service.is_downloading("facebook/mms-tts-eng") is False


# ---------------------------------------------------------------------------
# start_download SSE events
# ---------------------------------------------------------------------------

class TestStartDownload:
    @pytest.mark.anyio
    async def test_publishes_progress_events(self, service: ModelService, mock_tts_engine: MagicMock, event_bus: EventBus):
        """Download progress callback publishes SSE events."""
        queue = await event_bus.subscribe()

        def fake_download(model_id, progress_callback=None):
            if progress_callback:
                progress_callback(50)
                progress_callback(100)

        mock_tts_engine.download_model.side_effect = fake_download

        loop = asyncio.get_running_loop()
        service.start_download("facebook/mms-tts-eng", loop)

        # Wait for background thread
        await asyncio.sleep(0.2)

        messages = []
        while not queue.empty():
            messages.append(queue.get_nowait())

        combined = "".join(messages)
        assert "download-progress" in combined
        assert "download-completed" in combined
        assert "facebook/mms-tts-eng" in combined

    @pytest.mark.anyio
    async def test_publishes_failed_event_on_error(self, service: ModelService, mock_tts_engine: MagicMock, event_bus: EventBus):
        """Failed download publishes download-failed SSE event."""
        queue = await event_bus.subscribe()

        mock_tts_engine.download_model.side_effect = ModelLoadError("Network error")

        loop = asyncio.get_running_loop()
        service.start_download("facebook/mms-tts-eng", loop)

        await asyncio.sleep(0.2)

        messages = []
        while not queue.empty():
            messages.append(queue.get_nowait())

        combined = "".join(messages)
        assert "download-failed" in combined
        assert "Network error" in combined

    @pytest.mark.anyio
    async def test_clears_downloading_state_on_failure(self, service: ModelService, mock_tts_engine: MagicMock):
        mock_tts_engine.download_model.side_effect = ModelLoadError("fail")

        loop = asyncio.get_running_loop()
        service.start_download("facebook/mms-tts-eng", loop)

        await asyncio.sleep(0.2)
        assert service.is_downloading("facebook/mms-tts-eng") is False


# ---------------------------------------------------------------------------
# load_model
# ---------------------------------------------------------------------------

class TestLoadModel:
    def test_delegates_to_tts_engine(self, service: ModelService, mock_tts_engine: MagicMock):
        service.load_model("facebook/mms-tts-eng")
        mock_tts_engine.load_model.assert_called_once_with("facebook/mms-tts-eng")

    def test_raises_model_load_error_on_non_vram_failure(self, service: ModelService, mock_tts_engine: MagicMock):
        mock_tts_engine.load_model.side_effect = ModelLoadError("Model not cached")
        with pytest.raises(ModelLoadError, match="not cached"):
            service.load_model("facebook/mms-tts-eng")

    def test_raises_insufficient_vram_error_with_structured_data(self, service: ModelService, mock_tts_engine: MagicMock):
        mock_tts_engine.load_model.side_effect = ModelLoadError(
            "Insufficient VRAM to load facebook/mms-tts-eng. Required: 300 MB, Available: 100 MB"
        )
        gpu_info = MagicMock()
        gpu_info.vram_free_mb = 100.0
        mock_tts_engine.get_gpu_status.return_value = gpu_info
        mock_tts_engine.get_model_size_mb.return_value = 200.0

        with pytest.raises(InsufficientVRAMError) as exc_info:
            service.load_model("facebook/mms-tts-eng")

        assert exc_info.value.required_mb == 300.0  # 200 * 1.5
        assert exc_info.value.available_mb == 100.0
