"""Model adapter abstraction for heterogeneous TTS models.

Each TTS model requires its own loading and inference procedure.
The ``ModelAdapter`` protocol defines the common interface that all
model-specific adapters must implement.  The adapter registry maps
HuggingFace model IDs to their concrete adapter classes.

New adapters are registered by importing them here and adding an entry
to ``_ADAPTER_REGISTRY``.
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

import numpy as np


@runtime_checkable
class ModelAdapter(Protocol):
    """Common interface for model-specific loading and inference.

    Each concrete adapter encapsulates the library-specific details of
    loading a TTS model onto a device, running inference, and releasing
    GPU memory.
    """

    def load(self, model_id: str, device: str) -> None:
        """Load model and any required tokenizer/processor onto *device*.

        Args:
            model_id: HuggingFace model ID (e.g. ``"hexgrad/Kokoro-82M"``).
            device: PyTorch device string (e.g. ``"cuda"``).
        """
        ...

    def synthesize(self, text: str, **kwargs: Any) -> np.ndarray:
        """Run TTS inference and return raw audio samples.

        Args:
            text: Input text to synthesize.
            **kwargs: Model-specific options (voice, language, etc.).

        Returns:
            1-D float32 numpy array of audio samples.
        """
        ...

    @property
    def sample_rate(self) -> int:
        """The output sample rate of the loaded model in Hz."""
        ...

    def unload(self) -> None:
        """Release GPU memory and any held resources."""
        ...


# ---------------------------------------------------------------------------
# Adapter registry
# ---------------------------------------------------------------------------

# Maps HuggingFace model ID -> concrete adapter class.
# Each TASK-loader-* task adds its adapter here upon implementation.
from local_tts.tts.adapters.cosyvoice3 import CosyVoice3Adapter
from local_tts.tts.adapters.f5_tts import F5TTSAdapter
from local_tts.tts.adapters.fish_s2_pro import FishS2ProAdapter
from local_tts.tts.adapters.kokoro import KokoroAdapter
from local_tts.tts.adapters.moss_ttsd import MOSSTTSDAdapter
from local_tts.tts.adapters.qwen3_tts import Qwen3TTSAdapter
from local_tts.tts.adapters.voxcpm2 import VoxCPM2Adapter
from local_tts.tts.adapters.xtts_v2 import XTTSV2Adapter

_ADAPTER_REGISTRY: dict[str, type[ModelAdapter]] = {
    "hexgrad/Kokoro-82M": KokoroAdapter,
    "openbmb/VoxCPM2": VoxCPM2Adapter,
    "OpenMOSS-Team/MOSS-TTSD-v1.0": MOSSTTSDAdapter,
    # Qwen3-TTS loads via the `qwen-tts` package, which requires transformers
    # 4.57.3 (and accelerate 1.12.0). It is usable when the exploratory backend
    # baseline is installed at transformers 4.57.3 — the version qwen-tts requires
    # (DEC-transformers-5x-baseline). At that baseline MOSS-TTSD / Higgs v3 (which
    # need transformers >=5.x) are not loadable at runtime; the trade-off is the
    # inverse and reversible. The adapter is registered and lazy-imports the
    # package (mocked in tests), mirroring the Fish S2-Pro pattern. The package is
    # a GPU-host dependency, not a backend runtime dependency (its hard
    # transformers pin must not silently drive a fresh `pip install -e .`).
    # Re-registered 2026-06-21.
    "Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice": Qwen3TTSAdapter,
    # fishaudio/s2-pro loads via the GitHub-only fish-speech package, which pins
    # transformers<=4.57.3 / torch==2.8.0 — mutually exclusive with MOSS-TTSD /
    # Higgs v3 (transformers>=5.x). The backend transformers baseline is
    # exploratory to accommodate this (DEC-transformers-5x-baseline); the package
    # is a GPU-host dependency (lazy-imported in the adapter, mocked in tests).
    "fishaudio/s2-pro": FishS2ProAdapter,
    # coqui/XTTS-v2 loads via the Coqui `TTS` / `coqui-tts` package, a heavy
    # GPU-host dependency that pins an older transformers/torch and is mutually
    # incompatible with this backend's baseline (DEC-transformers-5x-baseline) —
    # so it is NOT a backend runtime dependency. The adapter lazy-imports it
    # (clear install hint), tests mock it, and full-weight runtime validation is
    # a GPU-host step (the Fish S2-Pro / Qwen3-TTS pattern). Translate-ISO,
    # named-built-in-speaker + optional reference-wav cloning; 17 langs incl.
    # Italian; 24 kHz. ⚠️ Non-FOSS weights (CPML) — license notice in the UI.
    "coqui/XTTS-v2": XTTSV2Adapter,
    # FunAudioLLM/Fun-CosyVoice3-0.5B-2512 loads via the FunAudioLLM `cosyvoice`
    # package's own AutoModel (not HuggingFace's). The package hard-pins
    # transformers==4.51.3 / torch==2.3.1 / numpy==1.26.4, so — like qwen-tts /
    # fish-speech (DEC-transformers-5x-baseline) — it is a GPU-host dependency,
    # NOT a backend runtime dependency (it must not drive a fresh `pip install`).
    # The adapter lazy-imports it (clear install hint), tests mock it, and
    # full-weight runtime validation is a GPU-host step. Registered uniformly;
    # loadability is a runtime function of the installed environment. Auto-detect
    # language (Apache-2.0/FOSS); requires a reference voice clip (no built-in
    # speaker); 24 kHz.
    "FunAudioLLM/Fun-CosyVoice3-0.5B-2512": CosyVoice3Adapter,
    # SWivid/F5-TTS loads via the `f5-tts` package's high-level `F5TTS` API. The
    # package pins numpy<=1.26.4 on Python<=3.10 (conflicting with the baseline's
    # numpy 2.x) and pulls a heavy dependency tree, so — like cosyvoice /
    # qwen-tts / fish-speech (DEC-transformers-5x-baseline) — it is a GPU-host
    # dependency, NOT a backend runtime dependency (it must not drive a fresh
    # `pip install`). The adapter lazy-imports it (clear install hint), tests
    # mock it, and full-weight runtime validation is a GPU-host step. Registered
    # uniformly; loadability is a runtime function of the installed environment.
    # Auto-detect language; requires a reference voice clip (no built-in speaker);
    # 24 kHz. ⚠️ Non-FOSS weights (CC-BY-NC-4.0) — license notice in the UI.
    "SWivid/F5-TTS": F5TTSAdapter,
    # bosonai/higgs-audio-v3-tts-4b is intentionally NOT registered. Boson
    # publishes v3 ONLY as a vLLM-Omni / SGLang-Omni *server* — its model card
    # shows no transformers/Python path. Its `model_type: higgs_multimodal_qwen3`
    # is absent from transformers (released 5.12.1 and main) and the HF repo ships
    # no remote code (no auto_map / *.py), so `trust_remote_code` can't help and
    # it cannot be loaded in-process under DEC-single-process (verified 2026-06-21
    # against the runtime "does not recognize this architecture" failure). The
    # adapter module (`higgs_audio_v3.py`) + tests are kept on the bet that
    # transformers later adds native `higgs_multimodal_qwen3` support, at which
    # point re-register here. Until then the model lists with loader_available=false.
    # "bosonai/higgs-audio-v3-tts-4b": HiggsAudioV3Adapter,
    # "ResembleAI/chatterbox": ChatterboxAdapter,   # TASK-loader-chatterbox
    # ... (added by adapter implementation tasks)
}


def get_adapter(model_id: str) -> ModelAdapter | None:
    """Create a new adapter instance for *model_id*, or return ``None``."""
    adapter_cls = _ADAPTER_REGISTRY.get(model_id)
    if adapter_cls is None:
        return None
    return adapter_cls()


def has_adapter(model_id: str) -> bool:
    """Check whether a concrete adapter is registered for *model_id*."""
    return model_id in _ADAPTER_REGISTRY
