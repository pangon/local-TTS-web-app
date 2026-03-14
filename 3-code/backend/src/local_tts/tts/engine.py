"""TTSEngine — unified public interface for the TTS subpackage.

Assembles GPU validation, model management, chapter parsing, and synthesis
behind a single class. This is the only entry point that backend application
services should use. The class has no web-framework dependencies and can be
invoked from scripts or CLI tools (REQ-MNT-modular-ai-layer).
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Callable

from local_tts.tts.chapter_parser import Chapter, parse_chapters
from local_tts.tts.gpu_validator import (
    GPUInfo,
    GPUValidationError,
    VRAMCheckResult,
    check_vram,
    get_gpu_status,
    validate_gpu,
)
from local_tts.tts.model_loader import (
    DiskSpaceCheck,
    ModelInfo,
    ModelLoadError,
    ModelLoader,
)
from local_tts.tts.synthesizer import (
    SynthesisError,
    SynthesisResult,
    synthesize_chapters,
)

logger = logging.getLogger(__name__)


class TTSEngine:
    """Unified interface for all TTS inference and GPU interaction.

    Manages the lifecycle of TTS operations: GPU validation, model download/
    load/unload, chapter parsing, and audio synthesis. Designed to be
    independent of any web framework so it can be extracted into a standalone
    project without major refactoring.
    """

    def __init__(self) -> None:
        self._model_loader = ModelLoader()

    # ------------------------------------------------------------------
    # GPU validation
    # ------------------------------------------------------------------

    def validate_gpu(self) -> GPUInfo:
        """Verify NVIDIA GPU + CUDA availability.

        Raises:
            GPUValidationError: If no compatible GPU/CUDA is detected.
        """
        return validate_gpu()

    def get_gpu_status(self) -> GPUInfo | None:
        """Return current GPU info, or None if unavailable."""
        return get_gpu_status()

    def check_vram(self, required_mb: float) -> VRAMCheckResult:
        """Check whether sufficient VRAM is available.

        Raises:
            GPUValidationError: If no GPU is available.
        """
        return check_vram(required_mb)

    # ------------------------------------------------------------------
    # Model management
    # ------------------------------------------------------------------

    @property
    def loaded_model_id(self) -> str | None:
        """The HuggingFace ID of the currently loaded model, or None."""
        return self._model_loader.loaded_model_id

    def list_models(self) -> list[ModelInfo]:
        """List all compatible TTS models with cache and load status."""
        return self._model_loader.list_models()

    def is_model_cached(self, model_id: str) -> bool:
        """Check if a model is present in the local cache."""
        return self._model_loader.is_cached(model_id)

    def get_model_size_mb(self, model_id: str) -> float:
        """Estimate model size in MB via HuggingFace Hub API."""
        return self._model_loader.get_model_size_mb(model_id)

    def check_disk_space(self, model_id: str) -> DiskSpaceCheck:
        """Check if sufficient disk space exists for downloading a model."""
        return self._model_loader.check_disk_space(model_id)

    def download_model(
        self,
        model_id: str,
        progress_callback: Callable[[int], None] | None = None,
    ) -> None:
        """Download a model to the local HuggingFace cache.

        Args:
            model_id: HuggingFace model ID (e.g., "facebook/mms-tts-eng").
            progress_callback: Called with progress percentage (0-100).

        Raises:
            ModelLoadError: If the download fails.
        """
        self._model_loader.download_model(model_id, progress_callback)

    def load_model(self, model_id: str) -> None:
        """Load a cached model onto the GPU.

        Checks VRAM availability. Unloads any previously loaded model first.

        Raises:
            ModelLoadError: If the model is not cached, VRAM is insufficient,
                or loading fails.
        """
        self._model_loader.load_model(model_id)

    def unload_model(self) -> None:
        """Unload the currently loaded model from GPU memory."""
        self._model_loader.unload_model()

    # ------------------------------------------------------------------
    # Chapter parsing
    # ------------------------------------------------------------------

    def parse_chapters(self, text: str) -> list[Chapter]:
        """Parse text into chapters based on detected heading patterns.

        Returns a list of Chapter objects. When no chapter structure is
        detected, the entire text is returned as a single chapter.
        """
        return parse_chapters(text)

    # ------------------------------------------------------------------
    # Synthesis
    # ------------------------------------------------------------------

    def synthesize(
        self,
        text: str,
        output_dir: Path,
        progress_callback: Callable[[int], None] | None = None,
    ) -> list[SynthesisResult]:
        """Parse text into chapters and synthesize all to MP3 files.

        This is the high-level synthesis method that combines chapter parsing
        and audio synthesis. Each chapter is written to
        ``output_dir/chapter-NN.mp3``.

        Args:
            text: Full input text to convert to audio.
            output_dir: Directory where MP3 files will be written.
            progress_callback: Called with overall percentage (0-100).

        Returns:
            List of SynthesisResult, one per chapter.

        Raises:
            ModelLoadError: If no model is loaded.
            SynthesisError: If synthesis fails.
        """
        chapters = self.parse_chapters(text)
        return self.synthesize_chapters(chapters, output_dir, progress_callback)

    def synthesize_chapters(
        self,
        chapters: list[Chapter],
        output_dir: Path,
        progress_callback: Callable[[int], None] | None = None,
    ) -> list[SynthesisResult]:
        """Synthesize pre-parsed chapters to MP3 files.

        Use this when you need control over chapter parsing separately
        from synthesis (e.g., for preview of a single chapter).

        Args:
            chapters: Chapters to synthesize.
            output_dir: Directory where MP3 files will be written.
            progress_callback: Called with overall percentage (0-100).

        Returns:
            List of SynthesisResult, one per chapter.

        Raises:
            ModelLoadError: If no model is loaded.
            SynthesisError: If synthesis fails.
        """
        model = self._model_loader.model
        tokenizer = self._model_loader.tokenizer

        # MMS TTS models use a fixed 16 kHz sample rate
        sample_rate = getattr(model.config, "sampling_rate", 16000)

        return synthesize_chapters(
            chapters=chapters,
            model=model,
            tokenizer=tokenizer,
            sample_rate=sample_rate,
            output_dir=output_dir,
            progress_callback=progress_callback,
        )
