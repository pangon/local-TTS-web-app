"""HuggingFace model download, caching, and GPU loading.

Manages the lifecycle of TTS models: downloading from HuggingFace Hub,
checking cache status, verifying disk space, and loading onto GPU with
VRAM preflight checks.  Model loading and inference are delegated to
model-specific adapters (see ``local_tts.tts.adapters``).
"""

from __future__ import annotations

import logging
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import torch
from huggingface_hub import model_info as hf_model_info, scan_cache_dir, snapshot_download

from local_tts import config
from local_tts.tts.adapters import ModelAdapter, get_adapter, has_adapter
from local_tts.tts.gpu_validator import check_vram

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ModelCatalogEntry:
    """Static catalog metadata for a compatible TTS model.

    ``license`` is the model-weights license (an SPDX-style identifier or a
    short name). ``license_is_foss`` is ``True`` only when that license is
    OSI open-source (e.g. Apache-2.0, MIT); it is ``False`` for open-weight
    but research / non-commercial licenses. When ``license_is_foss`` is
    ``False`` a non-empty ``license_notice`` describing the usage terms must
    be present so the frontend can disclose them (``DEC-model-license-disclosure``).
    """

    name: str
    license: str
    license_is_foss: bool
    license_notice: str | None = None


# License metadata records the *model-weights* license verified against each
# model's HuggingFace card. Several models ship FOSS code but non-commercial
# weights (XTTS-v2, fish-speech, F5-TTS) — the weights license governs here,
# so those are marked non-FOSS with a disclosure notice (DEC-model-license-disclosure).
COMPATIBLE_MODELS: dict[str, ModelCatalogEntry] = {
    "ResembleAI/chatterbox": ModelCatalogEntry(
        name="Chatterbox Multilingual (MIT, 23 langs incl. Italian)",
        license="MIT",
        license_is_foss=True,
    ),
    "Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice": ModelCatalogEntry(
        name="Qwen3-TTS 1.7B (Apache 2.0, 10 langs incl. Italian)",
        license="Apache-2.0",
        license_is_foss=True,
    ),
    "FunAudioLLM/Fun-CosyVoice3-0.5B-2512": ModelCatalogEntry(
        name="CosyVoice 3 0.5B (Apache 2.0, 9 langs incl. Italian)",
        license="Apache-2.0",
        license_is_foss=True,
    ),
    "hexgrad/Kokoro-82M": ModelCatalogEntry(
        name="Kokoro 82M (Apache 2.0, Italian voices: if_sara, im_nicola)",
        license="Apache-2.0",
        license_is_foss=True,
    ),
    "openbmb/VoxCPM2": ModelCatalogEntry(
        name="VoxCPM2 (Apache 2.0, 30 langs incl. Italian, 48 kHz, ~8 GB VRAM)",
        license="Apache-2.0",
        license_is_foss=True,
    ),
    "OpenMOSS-Team/MOSS-TTSD-v1.0": ModelCatalogEntry(
        name=(
            "MOSS-TTSD v1.0 (Apache 2.0, 20 langs incl. Italian, "
            "dialogue/multi-speaker, 24 kHz, ~19 GB VRAM)"
        ),
        license="Apache-2.0",
        license_is_foss=True,
    ),
    "bosonai/higgs-audio-v2-generation-3B-base": ModelCatalogEntry(
        name="Higgs Audio V2 3B (Apache 2.0, Italian partial)",
        license="Apache-2.0",
        license_is_foss=True,
    ),
    "coqui/XTTS-v2": ModelCatalogEntry(
        name="XTTS-v2 (MPL-2.0/CPML, 17 langs, first-class Italian)",
        license="Coqui Public Model License (CPML)",
        license_is_foss=False,
        license_notice=(
            "Model weights under the Coqui Public Model License (CPML): free "
            "for non-commercial and personal use only; commercial use requires "
            "a separate license."
        ),
    ),
    "fishaudio/fish-speech-1.5": ModelCatalogEntry(
        name="Fish Speech v1.5 (CC-BY-NC-SA, Italian <10K hrs)",
        license="CC-BY-NC-SA-4.0",
        license_is_foss=False,
        license_notice=(
            "Creative Commons BY-NC-SA 4.0: free for non-commercial and "
            "personal use with attribution and share-alike; commercial use is "
            "not permitted."
        ),
    ),
    "fishaudio/s2-pro": ModelCatalogEntry(
        name="Fish Audio S2-Pro (Research License, 80+ langs incl. Italian, 44.1 kHz, 12–24 GB VRAM)",
        license="Fish Audio Research License",
        license_is_foss=False,
        license_notice=(
            "Fish Audio Research License: free for research, personal and other "
            "non-commercial use; commercial use requires a separate paid license."
        ),
    ),
    "canopylabs/orpheus-3b-0.1-ft": ModelCatalogEntry(
        name="Orpheus TTS 3B (Apache 2.0, Italian experimental)",
        license="Apache-2.0",
        license_is_foss=True,
    ),
    "SWivid/F5-TTS": ModelCatalogEntry(
        name="F5-TTS (MIT/CC-BY-NC, Italian cross-lingual only)",
        license="CC-BY-NC-4.0",
        license_is_foss=False,
        license_notice=(
            "Model weights under Creative Commons BY-NC 4.0 (the code is MIT): "
            "free for non-commercial and personal use; commercial use is not "
            "permitted."
        ),
    ),
    "parler-tts/parler-tts-mini-multilingual-v1.1": ModelCatalogEntry(
        name="Parler-TTS Mini Multilingual (Apache 2.0, 8 langs incl. Italian)",
        license="Apache-2.0",
        license_is_foss=True,
    ),
    "Zyphra/Zonos-v0.1-transformer": ModelCatalogEntry(
        name="Zonos 1.6B (Apache 2.0, Italian limited)",
        license="Apache-2.0",
        license_is_foss=True,
    ),
    "nari-labs/Dia-1.6B-0626": ModelCatalogEntry(
        name="Dia 1.6B (Apache 2.0, English only)",
        license="Apache-2.0",
        license_is_foss=True,
    ),
}


@dataclass(frozen=True)
class ModelInfo:
    """Information about a compatible TTS model."""

    model_id: str
    name: str
    is_cached: bool
    is_loaded: bool
    loader_available: bool
    license: str = ""
    license_is_foss: bool = True
    license_notice: str | None = None


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
    Only one model can be loaded on the GPU at a time.  Loading and
    inference are delegated to model-specific adapters.
    """

    def __init__(self) -> None:
        self._loaded_model_id: str | None = None
        self._adapter: ModelAdapter | None = None

    @property
    def loaded_model_id(self) -> str | None:
        return self._loaded_model_id

    @property
    def adapter(self) -> ModelAdapter:
        """The adapter for the currently loaded model.

        Raises:
            ModelLoadError: If no model is loaded.
        """
        if self._adapter is None:
            raise ModelLoadError("No model is currently loaded")
        return self._adapter

    def list_models(self) -> list[ModelInfo]:
        cached_ids = self._get_cached_model_ids()
        return [
            ModelInfo(
                model_id=mid,
                name=entry.name,
                is_cached=mid in cached_ids,
                is_loaded=mid == self._loaded_model_id,
                loader_available=has_adapter(mid),
                license=entry.license,
                license_is_foss=entry.license_is_foss,
                license_notice=entry.license_notice,
            )
            for mid, entry in COMPATIBLE_MODELS.items()
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
        """Load a cached model onto the GPU via its model adapter.

        Checks VRAM availability before loading. Unloads any previously
        loaded model first.

        Raises:
            ModelLoadError: If no adapter is available for the model, the
                model is not cached, VRAM is insufficient, or loading fails.
        """
        if self._loaded_model_id == model_id:
            logger.info("Model %s is already loaded", model_id)
            return

        if not has_adapter(model_id):
            raise ModelLoadError(
                f"No adapter available for model {model_id}. "
                "This model cannot be loaded yet."
            )

        if not self.is_cached(model_id):
            raise ModelLoadError(
                f"Model {model_id} is not cached. Download it first."
            )

        # Unload current model to free GPU memory before VRAM check
        if self._loaded_model_id is not None:
            self.unload_model()

        # Estimate VRAM requirement from cached model size. The overhead factor
        # is configurable (LOCAL_TTS_VRAM_OVERHEAD_FACTOR) so the guard can be
        # tuned for a borderline model on a smaller GPU (REQ-F-gpu-validation).
        model_size_mb = self._get_cached_model_size_mb(model_id)
        estimated_vram_mb = model_size_mb * config.VRAM_OVERHEAD_FACTOR

        vram_result = check_vram(estimated_vram_mb)
        if not vram_result.sufficient:
            raise ModelLoadError(
                f"Insufficient VRAM to load {model_id}. "
                f"Required: {vram_result.required_mb:.0f} MB, "
                f"Available: {vram_result.available_mb:.0f} MB"
            )

        logger.info("Loading model %s onto GPU", model_id)
        try:
            adapter = get_adapter(model_id)
            assert adapter is not None  # guarded by has_adapter above
            adapter.load(model_id, "cuda")
            self._adapter = adapter
            self._loaded_model_id = model_id
            logger.info("Model %s loaded successfully", model_id)
        except Exception as exc:
            logger.exception("Failed to load model %s", model_id)
            self._adapter = None
            self._loaded_model_id = None
            raise ModelLoadError(
                f"Failed to load model {model_id}: {exc}"
            ) from exc

    def unload_model(self) -> None:
        """Unload the currently loaded model from GPU memory."""
        if self._loaded_model_id is None:
            return
        logger.info("Unloading model %s", self._loaded_model_id)
        if self._adapter is not None:
            self._adapter.unload()
        self._adapter = None
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
    """Create a tqdm subclass that reports aggregate download progress.

    Subclasses the real ``tqdm.tqdm`` so that the full interface
    (iteration, locking, display methods) is inherited.  Only
    ``update`` is overridden to forward byte-level progress to a
    percentage-based *callback*.
    """
    from tqdm.auto import tqdm as _tqdm_base

    try:
        info = hf_model_info(model_id, files_metadata=True)
        total_size = sum(
            s.size for s in (info.siblings or []) if s.size is not None
        )
    except Exception:
        total_size = 0

    state = {"downloaded": 0, "last_pct": -1}

    class _ProgressTqdm(_tqdm_base):  # type: ignore[misc]
        """tqdm subclass forwarding progress to a callback."""

        def __init__(self, *args: object, **kwargs: object) -> None:
            kwargs["disable"] = True  # suppress terminal output
            super().__init__(*args, **kwargs)

        def update(self, n: float = 1) -> bool | None:
            state["downloaded"] += int(n)
            if total_size > 0:
                pct = min(int(state["downloaded"] / total_size * 100), 99)
                if pct != state["last_pct"]:
                    state["last_pct"] = pct
                    callback(pct)
            return super().update(n)

    return _ProgressTqdm
