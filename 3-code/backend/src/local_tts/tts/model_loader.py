"""HuggingFace model download, caching, and GPU loading.

Manages the lifecycle of TTS models: downloading from HuggingFace Hub,
checking cache status, verifying disk space, and loading onto GPU with
VRAM preflight checks.
"""

from __future__ import annotations

import logging
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import torch
from huggingface_hub import model_info as hf_model_info, scan_cache_dir, snapshot_download
from transformers import AutoModel, AutoTokenizer

from local_tts.tts.gpu_validator import check_vram

logger = logging.getLogger(__name__)

_VRAM_OVERHEAD_FACTOR = 1.5

COMPATIBLE_MODELS: dict[str, str] = {
    "ResembleAI/chatterbox": "Chatterbox Multilingual (MIT, 23 langs incl. Italian)",
    "Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice": "Qwen3-TTS 1.7B (Apache 2.0, 10 langs incl. Italian)",
    "FunAudioLLM/Fun-CosyVoice3-0.5B-2512": "CosyVoice 3 0.5B (Apache 2.0, 9 langs incl. Italian)",
    "hexgrad/Kokoro-82M": "Kokoro 82M (Apache 2.0, Italian voices: if_sara, im_nicola)",
    "bosonai/higgs-audio-v2-generation-3B-base": "Higgs Audio V2 3B (Apache 2.0, Italian partial)",
    "coqui/XTTS-v2": "XTTS-v2 (MPL-2.0/CPML, 17 langs, first-class Italian)",
    "fishaudio/fish-speech-1.5": "Fish Speech v1.5 (CC-BY-NC-SA, Italian <10K hrs)",
    "canopylabs/orpheus-3b-0.1-ft": "Orpheus TTS 3B (Apache 2.0, Italian experimental)",
    "SWivid/F5-TTS": "F5-TTS (MIT/CC-BY-NC, Italian cross-lingual only)",
    "parler-tts/parler-tts-mini-multilingual-v1.1": "Parler-TTS Mini Multilingual (Apache 2.0, 8 langs incl. Italian)",
    "Zyphra/Zonos-v0.1-transformer": "Zonos 1.6B (Apache 2.0, Italian limited)",
    "nari-labs/Dia-1.6B-0626": "Dia 1.6B (Apache 2.0, English only)",
}


@dataclass(frozen=True)
class ModelInfo:
    """Information about a compatible TTS model."""

    model_id: str
    name: str
    is_cached: bool
    is_loaded: bool


@dataclass(frozen=True)
class DiskSpaceCheck:
    """Result of a disk space preflight check."""

    sufficient: bool
    estimated_mb: float
    available_mb: float


class ModelLoadError(Exception):
    """Raised when model download or loading fails."""


class ModelLoader:
    """Manages HuggingFace TTS model download, caching, and GPU loading.

    Models are stored in the HuggingFace Hub default cache directory.
    Only one model can be loaded on the GPU at a time.
    """

    def __init__(self) -> None:
        self._loaded_model_id: str | None = None
        self._model: torch.nn.Module | None = None
        self._tokenizer: object | None = None

    @property
    def loaded_model_id(self) -> str | None:
        return self._loaded_model_id

    @property
    def model(self) -> torch.nn.Module:
        if self._model is None:
            raise ModelLoadError("No model is currently loaded")
        return self._model

    @property
    def tokenizer(self) -> object:
        if self._tokenizer is None:
            raise ModelLoadError("No model is currently loaded")
        return self._tokenizer

    def list_models(self) -> list[ModelInfo]:
        cached_ids = self._get_cached_model_ids()
        return [
            ModelInfo(
                model_id=mid,
                name=name,
                is_cached=mid in cached_ids,
                is_loaded=mid == self._loaded_model_id,
            )
            for mid, name in COMPATIBLE_MODELS.items()
        ]

    def is_cached(self, model_id: str) -> bool:
        return model_id in self._get_cached_model_ids()

    def get_model_size_mb(self, model_id: str) -> float:
        """Estimate model size in MB using HuggingFace Hub API.

        Returns 0.0 if size cannot be determined (e.g., no internet).
        """
        try:
            info = hf_model_info(model_id, files_metadata=True)
            total_bytes = sum(
                s.size for s in (info.siblings or []) if s.size is not None
            )
            return total_bytes / (1024 * 1024)
        except Exception:
            logger.warning("Could not determine size for model %s", model_id)
            return 0.0

    def check_disk_space(self, model_id: str) -> DiskSpaceCheck:
        """Check if sufficient disk space is available for downloading a model."""
        estimated_mb = self.get_model_size_mb(model_id)
        cache_dir = _get_cache_dir()
        cache_dir.mkdir(parents=True, exist_ok=True)
        usage = shutil.disk_usage(cache_dir)
        available_mb = usage.free / (1024 * 1024)
        return DiskSpaceCheck(
            sufficient=available_mb >= estimated_mb,
            estimated_mb=round(estimated_mb, 1),
            available_mb=round(available_mb, 1),
        )

    def download_model(
        self,
        model_id: str,
        progress_callback: Callable[[int], None] | None = None,
    ) -> None:
        """Download a model to the local HuggingFace cache.

        Args:
            model_id: HuggingFace model ID (e.g., "ResembleAI/chatterbox").
            progress_callback: Called with progress percentage (0-100).

        Raises:
            ModelLoadError: If the download fails.
        """
        if self.is_cached(model_id):
            logger.info("Model %s is already cached", model_id)
            if progress_callback:
                progress_callback(100)
            return

        logger.info("Downloading model %s", model_id)
        try:
            tqdm_class = None
            if progress_callback:
                tqdm_class = _make_progress_tqdm(model_id, progress_callback)

            snapshot_download(model_id, tqdm_class=tqdm_class)

            if progress_callback:
                progress_callback(100)
            logger.info("Model %s downloaded successfully", model_id)
        except Exception as exc:
            raise ModelLoadError(
                f"Failed to download model {model_id}: {exc}"
            ) from exc

    def load_model(self, model_id: str) -> None:
        """Load a cached model onto the GPU.

        Checks VRAM availability before loading. Unloads any previously
        loaded model first.

        Raises:
            ModelLoadError: If the model is not cached, VRAM is insufficient,
                or loading fails.
        """
        if self._loaded_model_id == model_id:
            logger.info("Model %s is already loaded", model_id)
            return

        if not self.is_cached(model_id):
            raise ModelLoadError(
                f"Model {model_id} is not cached. Download it first."
            )

        # Unload current model to free GPU memory before VRAM check
        if self._loaded_model_id is not None:
            self.unload_model()

        # Estimate VRAM requirement from cached model size
        model_size_mb = self._get_cached_model_size_mb(model_id)
        estimated_vram_mb = model_size_mb * _VRAM_OVERHEAD_FACTOR

        vram_result = check_vram(estimated_vram_mb)
        if not vram_result.sufficient:
            raise ModelLoadError(
                f"Insufficient VRAM to load {model_id}. "
                f"Required: {vram_result.required_mb:.0f} MB, "
                f"Available: {vram_result.available_mb:.0f} MB"
            )

        logger.info("Loading model %s onto GPU", model_id)
        try:
            self._tokenizer = AutoTokenizer.from_pretrained(model_id)
            self._model = AutoModel.from_pretrained(model_id).to("cuda")
            self._loaded_model_id = model_id
            logger.info("Model %s loaded successfully", model_id)
        except Exception as exc:
            self._model = None
            self._tokenizer = None
            self._loaded_model_id = None
            raise ModelLoadError(
                f"Failed to load model {model_id}: {exc}"
            ) from exc

    def unload_model(self) -> None:
        """Unload the currently loaded model from GPU memory."""
        if self._loaded_model_id is None:
            return
        logger.info("Unloading model %s", self._loaded_model_id)
        self._model = None
        self._tokenizer = None
        self._loaded_model_id = None
        if torch.cuda.is_available():
            torch.cuda.empty_cache()

    def _get_cached_model_ids(self) -> set[str]:
        try:
            cache_info = scan_cache_dir()
            return {repo.repo_id for repo in cache_info.repos}
        except Exception:
            logger.warning("Could not scan HuggingFace cache")
            return set()

    def _get_cached_model_size_mb(self, model_id: str) -> float:
        try:
            cache_info = scan_cache_dir()
            for repo in cache_info.repos:
                if repo.repo_id == model_id:
                    return repo.size_on_disk / (1024 * 1024)
        except Exception:
            pass
        return self.get_model_size_mb(model_id)


def _get_cache_dir() -> Path:
    from huggingface_hub.constants import HF_HUB_CACHE

    return Path(HF_HUB_CACHE)


def _make_progress_tqdm(
    model_id: str,
    callback: Callable[[int], None],
) -> type:
    """Create a tqdm-compatible class that reports aggregate download progress."""
    try:
        info = hf_model_info(model_id, files_metadata=True)
        total_size = sum(
            s.size for s in (info.siblings or []) if s.size is not None
        )
    except Exception:
        total_size = 0

    state = {"downloaded": 0, "last_pct": -1}

    class _ProgressTqdm:
        """Minimal tqdm-compatible wrapper forwarding progress to a callback."""

        def __init__(self, *args, **kwargs):
            pass

        def update(self, n: int = 1) -> None:
            state["downloaded"] += n
            if total_size > 0:
                pct = min(int(state["downloaded"] / total_size * 100), 99)
                if pct != state["last_pct"]:
                    state["last_pct"] = pct
                    callback(pct)

        def close(self) -> None:
            pass

        def set_description(self, *args: object, **kwargs: object) -> None:
            pass

        def set_postfix(self, *args: object, **kwargs: object) -> None:
            pass

        def set_postfix_str(self, *args: object, **kwargs: object) -> None:
            pass

        def refresh(self, *args: object, **kwargs: object) -> None:
            pass

        def __enter__(self) -> _ProgressTqdm:
            return self

        def __exit__(self, *args: object) -> None:
            self.close()

    return _ProgressTqdm
