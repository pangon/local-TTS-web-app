"""XTTS-v2 adapter using the Coqui ``TTS`` package.

Loads ``coqui/XTTS-v2`` via the low-level ``Xtts`` model API from the
HuggingFace-cached snapshot and runs multilingual TTS inference locally on GPU.
XTTS-v2 is a cross-lingual voice-cloning model with 17 languages (first-class
Italian), ~58 built-in studio speakers, and 24 kHz output.

Unlike the auto-detect models (VoxCPM2, MOSS-TTSD, Fish S2-Pro), XTTS-v2 takes
an **explicit language** argument, so this adapter *translates* the application's
ISO 639-1 code to XTTS's own code — mostly identity (``it`` -> ``it``); only
Chinese differs (``zh`` -> ``zh-cn``) — exactly like the Kokoro and Qwen3-TTS
adapters (architecture § Model-Specific Loading Requirements).

Voice control:
  - ``voice``: built-in studio speaker name (default ``_DEFAULT_SPEAKER``). XTTS
    has no Italian-named speaker, but all studio speakers are cross-lingual and
    produce Italian phonemes for Italian text with ``language="it"`` — the same
    situation as Qwen3-TTS (``DEC-default-italian-language``).
  - ``speaker_wav``: optional path to a reference clip for zero-shot voice
    cloning; when given it overrides the built-in speaker.

⚠️ **License: Coqui Public Model License (CPML) — non-commercial / personal use,
NOT FOSS** (free for personal/local use; commercial use requires a separate
license).  Surfaced with a frontend license notice per
``DEC-model-license-disclosure``.

Decision: DEC-default-italian-language — the default language is Italian.

.. note::
   **Text normalization.** XTTS-v2 applies tokenizer-level text cleaning
   (``multilingual_cleaners`` + number/abbreviation expansion) inside
   ``inference`` and exposes **no public flag to disable it**.  Because the
   application already feeds the exact user-confirmed, preprocessed text
   (``DEC-preprocess-review-flow``) — numbers/dates/abbreviations are verbalized
   upstream — XTTS's expansion is largely a no-op on that text; this residual
   internal cleaning is a documented limitation, unlike VoxCPM2/Fish S2-Pro which
   accept ``normalize=False``.

.. note::
   **Packaging / runtime.** The Coqui ``TTS`` package is a heavy dependency: the
   original ``TTS`` (``0.22.0``, archived after Coqui AI shut down) pins an older
   ``transformers`` / ``torch`` and does not support modern Python, while the
   actively-maintained ``coqui-tts`` fork (idiap) runs on Python 3.10-3.12 +
   recent PyTorch but still constrains the stack.  Either way it is mutually
   incompatible with this repo's transformers/torch baseline
   (``DEC-transformers-5x-baseline``), so it is **not** a backend runtime
   dependency: ``load()`` lazy-imports it (raising a clear install hint), unit
   tests mock it, and full-weight runtime validation against the real model is a
   GPU-host step (the Fish S2-Pro / Qwen3-TTS precedent).  On the GPU host,
   install it in a dedicated environment::

       pip install coqui-tts        # maintained fork; Python 3.10-3.12 + recent torch
       # or the archived original:  pip install TTS   (Python < 3.12)
"""

from __future__ import annotations

import gc
import logging
from pathlib import Path
from typing import Any

import numpy as np
import torch

logger = logging.getLogger(__name__)

# Output sample rate for XTTS-v2 (24 kHz). Read from the loaded config at load
# time when available; this is the fallback.
_SAMPLE_RATE_DEFAULT = 24000

# Config file name inside the cached model snapshot (alongside model.pth,
# vocab.json and speakers_xtts.pth).
_CONFIG_FILENAME = "config.json"

# Default language used when none is supplied (DEC-default-italian-language).
# ISO 639-1 code, the convention spoken by the application layer.
_DEFAULT_LANGUAGE = "it"

# Default built-in studio speaker. XTTS-v2 has no Italian-named speaker; every
# studio speaker is cross-lingual, so this produces Italian phonemes for Italian
# text with language="it" (DEC-default-italian-language). Overridable via the
# ``voice`` kwarg, or bypassed entirely by supplying ``speaker_wav``.
_DEFAULT_SPEAKER = "Claribel Dervla"

# XTTS-v2's own 17 language codes. These are ISO 639-1 codes except Chinese,
# which XTTS identifies as "zh-cn".
_XTTS_LANGUAGES: frozenset[str] = frozenset(
    {
        "en", "es", "fr", "de", "it", "pt", "pl", "tr", "ru",
        "nl", "cs", "ar", "zh-cn", "ja", "hu", "ko", "hi",
    }
)

# ISO 639-1 codes whose XTTS identifier differs from the bare ISO code. The
# application layer speaks ISO codes (e.g. "it" per DEC-default-italian-language,
# also produced by the preprocessing pipeline); the adapter translates them here.
_LANG_CODE_BY_ISO: dict[str, str] = {
    "zh": "zh-cn",  # Mandarin Chinese
}


class XTTSV2Adapter:
    """Model adapter for ``coqui/XTTS-v2`` via the Coqui ``TTS`` package.

    Loads the model with the low-level ``Xtts`` API from the cached HuggingFace
    snapshot (downloaded by the Model Loader) and runs inference via
    ``Xtts.synthesize`` — using a built-in studio speaker by default, or zero-shot
    cloning from a reference clip when ``speaker_wav`` is supplied.
    """

    def __init__(self) -> None:
        self._model: Any | None = None
        self._config: Any | None = None
        self._device: str | None = None
        self._sample_rate: int = _SAMPLE_RATE_DEFAULT

    def load(self, model_id: str, device: str) -> None:
        """Load XTTS-v2 onto *device* via the low-level ``Xtts`` API.

        Resolves the cached model snapshot (downloaded by the Model Loader),
        loads the config and checkpoint from it, and moves the model onto
        *device* for GPU inference (``CON-gpu-inference``).

        Raises:
            RuntimeError: If the Coqui ``TTS`` package is not installed (it is a
                GPU-host dependency — see the module docstring).
        """
        try:
            from TTS.tts.configs.xtts_config import XttsConfig
            from TTS.tts.models.xtts import Xtts
        except ImportError as exc:
            raise RuntimeError(
                "The Coqui 'TTS' package is required for coqui/XTTS-v2 but is "
                "not installed. It pins an older transformers/torch and is "
                "mutually incompatible with this backend's baseline "
                "(DEC-transformers-5x-baseline), so install it in a dedicated "
                "environment on the GPU host:\n"
                "  pip install coqui-tts        # maintained fork (Python 3.10-3.12)\n"
                "  # or the archived original:  pip install TTS   (Python < 3.12)\n"
                f"(original import error: {exc})"
            ) from exc

        snapshot_dir = self._resolve_snapshot(model_id)
        config_path = str(Path(snapshot_dir) / _CONFIG_FILENAME)

        logger.info("Loading XTTS-v2 model %s on %s", model_id, device)
        config = XttsConfig()
        config.load_json(config_path)

        model = Xtts.init_from_config(config)
        # use_deepspeed=False: DeepSpeed is an optional heavy dependency we do
        # not require. eval=True puts the model in inference mode.
        model.load_checkpoint(
            config,
            checkpoint_dir=snapshot_dir,
            eval=True,
            use_deepspeed=False,
        )
        model.to(device)

        self._model = model
        self._config = config
        self._device = device
        self._sample_rate = self._read_sample_rate(config)
        logger.info(
            "XTTS-v2 model loaded successfully (%d Hz)", self._sample_rate
        )

    def synthesize(self, text: str, **kwargs: Any) -> np.ndarray:
        """Synthesize *text* and return a 1-D float32 numpy array.

        Keyword Args:
            voice: Built-in studio speaker name (e.g. ``"Claribel Dervla"``).
                   Defaults to ``_DEFAULT_SPEAKER``. Ignored when ``speaker_wav``
                   is given.
            speaker_wav: Optional path to a reference audio clip for zero-shot
                         voice cloning. When supplied, the built-in speaker is
                         bypassed and the model clones this voice.
            language: ISO 639-1 code (e.g. ``"it"``, ``"en"``) or a native XTTS
                      code (e.g. ``"zh-cn"``). Translated to XTTS's identifier;
                      defaults to Italian (``DEC-default-italian-language``).

        Raises:
            RuntimeError: If called before ``load()``.
            ValueError: If ``language`` is neither a recognized ISO 639-1 code
                nor a native XTTS language code.
        """
        if self._model is None:
            raise RuntimeError(
                "XTTSV2Adapter.load() must be called before synthesize()"
            )

        language = self._resolve_language(kwargs.get("language"))
        speaker_wav: str | None = kwargs.get("speaker_wav") or None

        # A reference clip (speaker_wav) takes precedence and triggers zero-shot
        # cloning; otherwise use a named built-in studio speaker.
        if speaker_wav is not None:
            speaker_id: str | None = None
        else:
            speaker_id = self._resolve_speaker(kwargs.get("voice") or _DEFAULT_SPEAKER)

        out = self._model.synthesize(
            text,
            self._config,
            speaker_wav=speaker_wav,
            language=language,
            speaker_id=speaker_id,
        )
        return self._extract_wav(out)

    @property
    def sample_rate(self) -> int:
        """The output sample rate of the loaded model in Hz (24 kHz)."""
        return self._sample_rate

    def unload(self) -> None:
        """Release GPU memory held by the XTTS-v2 model."""
        if self._model is not None:
            del self._model
            self._model = None

        self._config = None
        self._device = None

        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()

        logger.info("XTTS-v2 adapter unloaded")

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _resolve_speaker(self, requested: str) -> str:
        """Resolve *requested* to a valid built-in studio speaker name.

        ``Xtts.synthesize`` looks the speaker up in
        ``model.speaker_manager.speakers`` with a raw dict access that would
        ``KeyError`` on an unknown name. When the loaded model exposes a real
        speaker mapping, validate against it and fall back to the first available
        speaker (with a warning) so a stale default never hard-fails; when the
        mapping is unavailable (e.g. mocked in tests), pass the name through.
        """
        speakers = getattr(
            getattr(self._model, "speaker_manager", None), "speakers", None
        )
        if isinstance(speakers, dict) and speakers:
            if requested in speakers:
                return requested
            fallback = next(iter(speakers))
            logger.warning(
                "Speaker %r is not a built-in XTTS-v2 speaker; using %r instead. "
                "Available: %s",
                requested,
                fallback,
                ", ".join(sorted(speakers)),
            )
            return fallback
        return requested

    def _extract_wav(self, out: Any) -> np.ndarray:
        """Coerce the model's output to a 1-D float32 numpy array.

        ``Xtts.synthesize`` / ``inference`` return ``{"wav": <array>}``; tolerate
        a bare array too. Returns 0.1 s of silence on empty/None output.
        """
        wav = out.get("wav") if isinstance(out, dict) else out
        if wav is None:
            return self._silence()
        if isinstance(wav, torch.Tensor):
            wav = wav.detach().cpu().to(torch.float32).numpy()
        audio = np.asarray(wav, dtype=np.float32).reshape(-1)
        if audio.size == 0:
            return self._silence()
        return audio

    def _silence(self) -> np.ndarray:
        """Return 0.1 s of silence at the model's sample rate."""
        return np.zeros(int(self._sample_rate * 0.1), dtype=np.float32)

    @staticmethod
    def _resolve_snapshot(model_id: str) -> str:
        """Resolve the local path of the cached model snapshot.

        ``snapshot_download`` returns the existing cache path without
        re-downloading when the model is already cached (the Model Loader
        downloads it first).
        """
        from huggingface_hub import snapshot_download

        return snapshot_download(model_id)

    @staticmethod
    def _read_sample_rate(config: Any) -> int:
        """Read the output sample rate from the XTTS config, with a safe default.

        XTTS reports its output rate as ``config.audio.output_sample_rate``
        (24 kHz for XTTS-v2).
        """
        audio = getattr(config, "audio", None)
        value = getattr(audio, "output_sample_rate", None)
        try:
            if value is not None:
                return int(value)
        except (TypeError, ValueError):
            pass
        return _SAMPLE_RATE_DEFAULT

    @staticmethod
    def _resolve_language(value: str | None) -> str:
        """Resolve *value* to an XTTS-v2 language code.

        Accepts a native XTTS code (e.g. ``"it"``, ``"zh-cn"``) for backward
        compatibility, or an ISO 639-1 code which is translated to XTTS's
        identifier (mostly identity; ``zh`` -> ``zh-cn``). ``None`` or an empty
        string falls back to Italian (``DEC-default-italian-language``).

        Returns:
            The XTTS-v2 language code to forward to the model.

        Raises:
            ValueError: If *value* is neither a native XTTS code nor a
                recognized ISO 639-1 code.
        """
        if value is None or value.strip() == "":
            return _DEFAULT_LANGUAGE

        code = value.strip().lower()
        # Native XTTS code (covers the ISO-identity codes like "it", "en", and
        # the multi-part "zh-cn").
        if code in _XTTS_LANGUAGES:
            return code
        # ISO 639-1 code whose XTTS identifier differs (e.g. "zh" -> "zh-cn").
        if code in _LANG_CODE_BY_ISO:
            return _LANG_CODE_BY_ISO[code]

        raise ValueError(
            f"Unsupported language {value!r} for XTTS-v2. Use an ISO 639-1 code "
            f"or a native XTTS code "
            f"({', '.join(sorted(_XTTS_LANGUAGES))})."
        )
