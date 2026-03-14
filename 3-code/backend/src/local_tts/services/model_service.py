"""Model Service — application service for TTS model management.

Wraps TTSEngine model operations and coordinates with the EventBus to
publish download progress events via SSE (DEC-sse-progress). Model
downloads run in a background thread (DEC-single-process).
"""

from __future__ import annotations

import asyncio
import logging
import threading
from typing import Any

from local_tts.api.sse import EventBus
from local_tts.tts.engine import TTSEngine
from local_tts.tts.gpu_validator import GPUValidationError, VRAMCheckResult
from local_tts.tts.model_loader import DiskSpaceCheck, ModelInfo, ModelLoadError

logger = logging.getLogger(__name__)


class InsufficientVRAMError(Exception):
    """Raised when VRAM is insufficient for loading a model."""

    def __init__(self, required_mb: float, available_mb: float) -> None:
        self.required_mb = required_mb
        self.available_mb = available_mb
        super().__init__(
            f"Insufficient VRAM. Required: {required_mb:.0f} MB, "
            f"Available: {available_mb:.0f} MB"
        )


class ModelService:
    """Manages model listing, downloading, and loading.

    Coordinates between the TTSEngine (TTS subpackage) and the EventBus
    (SSE infrastructure) to provide model management with real-time
    progress updates.
    """

    def __init__(self, tts_engine: TTSEngine, event_bus: EventBus) -> None:
        self._tts_engine = tts_engine
        self._event_bus = event_bus
        self._download_lock = threading.Lock()
        self._downloading: set[str] = set()

    def list_models(self) -> list[ModelInfo]:
        """List all compatible TTS models with cache and load status."""
        return self._tts_engine.list_models()

    def check_disk_space(self, model_id: str) -> DiskSpaceCheck:
        """Check disk space availability for a model download."""
        return self._tts_engine.check_disk_space(model_id)

    def is_model_cached(self, model_id: str) -> bool:
        """Check if a model is already in the local cache."""
        return self._tts_engine.is_model_cached(model_id)

    def is_downloading(self, model_id: str) -> bool:
        """Check if a model download is currently in progress."""
        with self._download_lock:
            return model_id in self._downloading

    def start_download(self, model_id: str, loop: asyncio.AbstractEventLoop) -> None:
        """Start an asynchronous model download in a background thread.

        Progress is reported via SSE events (download-progress,
        download-completed, download-failed).

        Args:
            model_id: HuggingFace model ID to download.
            loop: The asyncio event loop for publishing SSE events.
        """
        with self._download_lock:
            self._downloading.add(model_id)

        thread = threading.Thread(
            target=self._download_worker,
            args=(model_id, loop),
            daemon=True,
        )
        thread.start()

    def load_model(self, model_id: str) -> None:
        """Load a cached model onto the GPU with VRAM preflight check.

        Raises:
            ModelLoadError: If the model is not cached or loading fails.
            InsufficientVRAMError: If VRAM is insufficient (with structured data).
            GPUValidationError: If no GPU is available for VRAM check.
        """
        try:
            self._tts_engine.load_model(model_id)
        except ModelLoadError as exc:
            if "Insufficient VRAM" in str(exc) or "VRAM" in str(exc):
                # Re-raise with structured VRAM data by querying GPU status
                gpu_info = self._tts_engine.get_gpu_status()
                available_mb = gpu_info.vram_free_mb if gpu_info else 0.0
                # Extract required from the model size estimate
                model_size_mb = self._tts_engine.get_model_size_mb(model_id)
                required_mb = model_size_mb * 1.5  # matches _VRAM_OVERHEAD_FACTOR
                raise InsufficientVRAMError(required_mb, available_mb) from exc
            raise

    def _download_worker(
        self, model_id: str, loop: asyncio.AbstractEventLoop
    ) -> None:
        """Background thread worker for model download."""
        try:

            def progress_callback(progress: int) -> None:
                self._publish_from_thread(
                    loop,
                    "download-progress",
                    {"model_id": model_id, "progress": progress},
                )

            self._tts_engine.download_model(model_id, progress_callback)

            self._publish_from_thread(
                loop,
                "download-completed",
                {"model_id": model_id},
            )
        except ModelLoadError as exc:
            logger.error("Model download failed for %s: %s", model_id, exc)
            self._publish_from_thread(
                loop,
                "download-failed",
                {"model_id": model_id, "error_message": str(exc)},
            )
        except Exception as exc:
            logger.error("Unexpected error downloading %s: %s", model_id, exc)
            self._publish_from_thread(
                loop,
                "download-failed",
                {"model_id": model_id, "error_message": str(exc)},
            )
        finally:
            with self._download_lock:
                self._downloading.discard(model_id)

    def _publish_from_thread(
        self,
        loop: asyncio.AbstractEventLoop,
        event_type: str,
        data: dict[str, Any],
    ) -> None:
        """Publish an SSE event from a background thread."""
        asyncio.run_coroutine_threadsafe(
            self._event_bus.publish(event_type, data),
            loop,
        )
