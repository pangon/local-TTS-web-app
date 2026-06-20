"""VoxCPM2 adapter using the ``voxcpm`` pip package.

Loads the ``openbmb/VoxCPM2`` model via ``VoxCPM.from_pretrained`` and runs
TTS inference locally on GPU.  VoxCPM2 is a tokenizer-free multilingual model
(30 languages including Italian) that **auto-detects the language from the
input text** — it takes no language tag.  Voice control is zero-shot: an
optional reference audio clip (with its transcript) clones a target voice;
without one the model uses its built-in voice.  Output sample rate is 48 kHz.

Decision: DEC-default-italian-language — the default language is Italian.
Because the model auto-detects the language, Italian input naturally yields
Italian phonemes; the ``language`` kwarg is accepted for interface uniformity
(architecture § Model-Specific Loading Requirements) but is advisory only — it
is validated and defaulted to Italian, not forwarded to the model.
"""

from __future__ import annotations

import gc
import logging
import re
from typing import Any

import numpy as np
import torch

logger = logging.getLogger(__name__)

# Output sample rate for VoxCPM2 (fixed by the model): 48 kHz. Higher than the
# typical 24 kHz; the synthesis pipeline reads the rate from ``sample_rate`` and
# pydub/ffmpeg encode any rate, so 48 kHz needs no special handling downstream.
_SAMPLE_RATE = 48000

# Default language used when none is supplied (DEC-default-italian-language).
# This is an ISO 639-1 code, the convention spoken by the application layer.
_DEFAULT_LANGUAGE = "it"

# A well-formed ISO 639-1 code is two ASCII letters.
_ISO_639_1_RE = re.compile(r"^[a-z]{2}$")


class VoxCPM2Adapter:
    """Model adapter for ``openbmb/VoxCPM2`` via the ``voxcpm`` package.

    Uses ``VoxCPM.from_pretrained`` to load the model (it selects CUDA
    automatically when available) and ``VoxCPM.generate`` for inference.
    The model auto-detects the input language, so no language identifier is
    passed at inference time; voice is controlled by an optional reference
    audio clip (zero-shot cloning).
    """

    def __init__(self) -> None:
        self._model: Any | None = None
        self._device: str | None = None

    def load(self, model_id: str, device: str) -> None:
        """Load VoxCPM2 onto *device* via ``VoxCPM.from_pretrained``.

        The model weights are downloaded/cached by HuggingFace Hub on first
        use.  The chosen *device* (e.g. ``"cuda"``) is passed through so
        inference runs on the GPU (``CON-gpu-inference``).
        """
        from voxcpm import VoxCPM

        logger.info("Loading VoxCPM2 model %s on %s", model_id, device)
        self._device = device
        self._model = VoxCPM.from_pretrained(model_id, device=device)
        logger.info("VoxCPM2 model loaded successfully")

    def synthesize(self, text: str, **kwargs: Any) -> np.ndarray:
        """Synthesize *text* and return a 1-D float32 numpy array.

        Keyword Args:
            voice: Optional path to a reference audio clip for zero-shot voice
                   cloning.  When omitted, the model's built-in voice is used
                   (Italian phonemes for Italian text, DEC-default-italian-language).
            prompt_text: Optional transcript of the reference audio clip; used
                         together with ``voice`` to improve cloning quality.
            language: ISO 639-1 code (e.g. ``"it"``, ``"en"``) or ``"auto"``.
                      VoxCPM2 auto-detects the language from the text, so this
                      value is validated and defaulted to Italian but is **not**
                      forwarded to the model (it is advisory).
            normalize: Whether to run VoxCPM2's built-in text normalizer.
                       Defaults to ``False`` because the application already
                       feeds the exact user-confirmed, preprocessed text
                       (DEC-preprocess-review-flow) — re-normalizing would
                       violate that guarantee.
            cfg_value: Optional classifier-free-guidance strength (model default
                       used when omitted).
            inference_timesteps: Optional diffusion step count (model default
                                 used when omitted).

        Raises:
            ValueError: If ``language`` is neither ``"auto"`` nor a well-formed
                ISO 639-1 code.
        """
        if self._model is None:
            raise RuntimeError("VoxCPM2Adapter.load() must be called before synthesize()")

        # Validate the language for a clear early error, even though the model
        # auto-detects and the value is not forwarded.
        self._resolve_language(kwargs.get("language"))

        prompt_wav_path: str | None = kwargs.get("voice") or None
        prompt_text: str | None = kwargs.get("prompt_text") or None
        normalize: bool = kwargs.get("normalize", False)

        gen_kwargs: dict[str, Any] = {
            "text": text,
            "prompt_wav_path": prompt_wav_path,
            "prompt_text": prompt_text,
            "normalize": normalize,
        }
        if kwargs.get("cfg_value") is not None:
            gen_kwargs["cfg_value"] = kwargs["cfg_value"]
        if kwargs.get("inference_timesteps") is not None:
            gen_kwargs["inference_timesteps"] = kwargs["inference_timesteps"]

        wav = self._model.generate(**gen_kwargs)

        if wav is None:
            return np.zeros(int(_SAMPLE_RATE * 0.1), dtype=np.float32)

        if isinstance(wav, torch.Tensor):
            wav = wav.cpu().numpy()

        audio = np.asarray(wav, dtype=np.float32).reshape(-1)
        if audio.size == 0:
            return np.zeros(int(_SAMPLE_RATE * 0.1), dtype=np.float32)

        return audio

    @property
    def sample_rate(self) -> int:
        """Output sample rate: 48 kHz."""
        return _SAMPLE_RATE

    def unload(self) -> None:
        """Release GPU memory held by the VoxCPM2 model."""
        if self._model is not None:
            del self._model
            self._model = None

        self._device = None

        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()

        logger.info("VoxCPM2 adapter unloaded")

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _resolve_language(value: str | None) -> str:
        """Validate *value* and resolve it to an ISO 639-1 code.

        VoxCPM2 auto-detects the spoken language from the text, so there is no
        model-specific language identifier to translate to (unlike Kokoro or
        Qwen3-TTS).  This method exists to honour the application's
        ISO-639-1-in convention and to fail clearly on a malformed value rather
        than silently mis-handling it.  ``None`` or an empty string falls back
        to the Italian default (``DEC-default-italian-language``); ``"auto"`` is
        accepted explicitly.

        Returns:
            The resolved ISO 639-1 code (or ``"auto"``). The caller does not
            forward it to the model — it is advisory only.

        Raises:
            ValueError: If *value* is neither ``"auto"`` nor a well-formed
                ISO 639-1 (two-letter) code.
        """
        if value is None or value.strip() == "":
            return _DEFAULT_LANGUAGE

        code = value.strip().lower()
        if code == "auto":
            return "auto"
        if _ISO_639_1_RE.match(code):
            return code

        raise ValueError(
            f"Unsupported language {value!r} for VoxCPM2. The model auto-detects "
            f"the language from the text; pass an ISO 639-1 code (e.g. 'it', "
            f"'en') or 'auto'."
        )
