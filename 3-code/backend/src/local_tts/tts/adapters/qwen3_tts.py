"""Qwen3-TTS adapter using the ``qwen-tts`` pip package.

Loads the Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice model via ``Qwen3TTSModel``
and runs TTS inference locally on GPU.  Supports speaker and language
selection via kwargs, plus optional instruction-based style control.

Decision: DEC-default-italian-language — defaults to Italian language.
"""

from __future__ import annotations

import gc
import logging
from typing import Any

import numpy as np
import torch

logger = logging.getLogger(__name__)

# Default language used when none is specified in kwargs (DEC-default-italian-language).
_DEFAULT_LANGUAGE = "Italian"

# Default speaker — Vivian has a clear, expressive voice suitable for audiobooks.
# No Italian-native speaker exists, but all speakers support cross-lingual synthesis.
_DEFAULT_SPEAKER = "Vivian"

# Supported speakers in the CustomVoice model.
SUPPORTED_SPEAKERS: tuple[str, ...] = (
    "Vivian",
    "Serena",
    "Uncle_Fu",
    "Dylan",
    "Eric",
    "Ryan",
    "Aiden",
    "Ono_Anna",
    "Sohee",
)

# Supported languages in the model.
SUPPORTED_LANGUAGES: tuple[str, ...] = (
    "Chinese",
    "English",
    "Japanese",
    "Korean",
    "German",
    "French",
    "Russian",
    "Portuguese",
    "Spanish",
    "Italian",
)


class Qwen3TTSAdapter:
    """Model adapter for Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice.

    Uses the ``qwen-tts`` package's ``Qwen3TTSModel`` for inference.
    The model supports 10 languages (including Italian) and 9 speakers
    with optional instruction-based style control.
    """

    def __init__(self) -> None:
        self._model: Any | None = None
        self._sample_rate: int = 24000  # Updated after first generation
        self._device: str | None = None

    def load(self, model_id: str, device: str) -> None:
        """Load Qwen3-TTS onto *device* via ``Qwen3TTSModel.from_pretrained``.

        The model weights are downloaded/cached by HuggingFace Hub on
        first use.  FlashAttention 2 is used when available for reduced
        memory usage, with automatic fallback to eager attention.
        """
        from qwen_tts import Qwen3TTSModel

        self._device = device

        # Determine attention implementation: prefer flash_attention_2 when available.
        attn_impl = self._detect_attn_implementation()

        if attn_impl is not None:
            logger.info(
                "Loading Qwen3-TTS model %s on %s with %s",
                model_id, device, attn_impl,
            )
        else:
            logger.warning(
                "Loading Qwen3-TTS model %s on %s WITHOUT FlashAttention 2 "
                "(higher VRAM usage). Install flash-attn for better performance: "
                "pip install flash-attn --no-build-isolation",
                model_id, device,
            )

        kwargs: dict[str, Any] = {
            "device_map": device,
            "dtype": torch.bfloat16,
        }
        if attn_impl is not None:
            kwargs["attn_implementation"] = attn_impl

        self._model = Qwen3TTSModel.from_pretrained(model_id, **kwargs)
        logger.info("Qwen3-TTS model loaded successfully")

    def synthesize(self, text: str, **kwargs: Any) -> np.ndarray:
        """Synthesize *text* and return a 1-D float32 numpy array.

        Keyword Args:
            voice: Speaker name (e.g. ``"Vivian"``, ``"Ryan"``).
                   Defaults to ``"Vivian"`` (DEC-default-italian-language).
            language: Full language name (e.g. ``"Italian"``, ``"English"``).
                      Defaults to ``"Italian"``.
            instruct: Optional style instruction (e.g. ``"Read slowly and calmly"``).
                      Defaults to empty string.
        """
        if self._model is None:
            raise RuntimeError("Qwen3TTSAdapter.load() must be called before synthesize()")

        speaker: str = kwargs.get("voice", _DEFAULT_SPEAKER)
        language: str = kwargs.get("language", _DEFAULT_LANGUAGE)
        instruct: str = kwargs.get("instruct", "")

        wavs, sr = self._model.generate_custom_voice(
            text=text,
            language=language,
            speaker=speaker,
            instruct=instruct,
        )

        self._sample_rate = int(sr)

        if not wavs or wavs[0] is None or len(wavs[0]) == 0:
            return np.zeros(int(self._sample_rate * 0.1), dtype=np.float32)

        audio = wavs[0]
        if isinstance(audio, torch.Tensor):
            audio = audio.cpu().numpy()

        return np.asarray(audio, dtype=np.float32)

    @property
    def sample_rate(self) -> int:
        """The output sample rate of the loaded model in Hz."""
        return self._sample_rate

    def unload(self) -> None:
        """Release GPU memory held by the Qwen3-TTS model."""
        if self._model is not None:
            del self._model
            self._model = None

        self._device = None

        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()

        logger.info("Qwen3-TTS adapter unloaded")

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _detect_attn_implementation() -> str | None:
        """Return ``"flash_attention_2"`` if flash-attn is installed, else ``None``."""
        try:
            import flash_attn  # noqa: F401
            return "flash_attention_2"
        except ImportError:
            logger.info(
                "flash-attn not installed; using default attention. "
                "Install flash-attn for reduced GPU memory usage."
            )
            return None
