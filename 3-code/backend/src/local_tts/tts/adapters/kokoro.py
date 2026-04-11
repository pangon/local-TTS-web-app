"""Kokoro-82M model adapter using the ``kokoro`` pip package.

Loads the hexgrad/Kokoro-82M model via ``KPipeline`` and runs TTS
inference locally on GPU.  Supports voice and language selection via
kwargs.

System dependency: ``espeak-ng`` is required for non-English G2P
(including Italian).  Install via ``apt-get install espeak-ng`` on
Debian/Ubuntu or the equivalent for your OS.
"""

from __future__ import annotations

import gc
import logging
from typing import Any

import numpy as np
import torch

logger = logging.getLogger(__name__)

# Output sample rate for Kokoro-82M (hardcoded by the model).
_SAMPLE_RATE = 24000

# Default language code used when none is specified in kwargs.
_DEFAULT_LANG_CODE = "a"  # American English


class KokoroAdapter:
    """Model adapter for hexgrad/Kokoro-82M via the ``kokoro`` package.

    Language is set at pipeline construction time.  When ``synthesize``
    is called with a ``language`` kwarg that differs from the current
    pipeline's language, the pipeline is transparently recreated while
    reusing the underlying ``KModel`` to avoid reloading weights.
    """

    def __init__(self) -> None:
        self._pipeline: Any | None = None
        self._model: Any | None = None
        self._current_lang_code: str | None = None
        self._device: str | None = None
        self._repo_id: str | None = None

    def load(self, model_id: str, device: str) -> None:
        """Load Kokoro-82M onto *device* via ``KPipeline``.

        The model weights are downloaded/cached by HuggingFace Hub on
        first use.
        """
        from kokoro import KPipeline

        logger.info("Loading Kokoro pipeline for %s on %s", model_id, device)
        self._repo_id = model_id
        self._device = device
        self._current_lang_code = _DEFAULT_LANG_CODE

        pipeline = KPipeline(
            lang_code=self._current_lang_code,
            repo_id=model_id,
            device=device,
        )
        self._pipeline = pipeline
        self._model = pipeline.model
        logger.info("Kokoro pipeline loaded successfully")

    def synthesize(self, text: str, **kwargs: Any) -> np.ndarray:
        """Synthesize *text* and return a 1-D float32 numpy array.

        Keyword Args:
            voice: Voice name (e.g. ``"af_heart"``, ``"if_sara"``).
                   Defaults to ``"af_heart"`` when not specified.
            language: Kokoro language code (e.g. ``"a"``, ``"i"``).
                      If it differs from the current pipeline language,
                      the pipeline is recreated (model weights are
                      reused).
            speed: Speech speed multiplier (float, default 1.0).
        """
        if self._pipeline is None:
            raise RuntimeError("KokoroAdapter.load() must be called before synthesize()")

        voice: str = kwargs.get("voice", "af_heart")
        language: str | None = kwargs.get("language")
        speed: float = kwargs.get("speed", 1.0)

        # Switch language if needed (reuses the loaded KModel).
        if language is not None and language != self._current_lang_code:
            self._switch_language(language)

        # Collect all audio chunks from the generator.
        chunks: list[np.ndarray] = []
        for result in self._pipeline(text, voice=voice, speed=speed):
            if result.audio is not None:
                chunks.append(result.audio.cpu().numpy())

        if not chunks:
            # Return a short silence if the model produced nothing.
            return np.zeros(int(_SAMPLE_RATE * 0.1), dtype=np.float32)

        return np.concatenate(chunks).astype(np.float32)

    @property
    def sample_rate(self) -> int:
        """Output sample rate: 24 kHz."""
        return _SAMPLE_RATE

    def unload(self) -> None:
        """Release GPU memory held by the Kokoro model."""
        if self._pipeline is not None:
            # Clear cached voice tensors.
            if hasattr(self._pipeline, "voices"):
                self._pipeline.voices.clear()
            self._pipeline = None

        if self._model is not None:
            del self._model
            self._model = None

        self._current_lang_code = None
        self._device = None
        self._repo_id = None

        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()

        logger.info("Kokoro adapter unloaded")

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _switch_language(self, lang_code: str) -> None:
        """Recreate the pipeline for a new language, reusing the KModel."""
        from kokoro import KPipeline

        logger.info(
            "Switching Kokoro language from %s to %s",
            self._current_lang_code,
            lang_code,
        )
        self._pipeline = KPipeline(
            lang_code=lang_code,
            repo_id=self._repo_id,
            model=self._model,
            device=self._device,
        )
        self._current_lang_code = lang_code
