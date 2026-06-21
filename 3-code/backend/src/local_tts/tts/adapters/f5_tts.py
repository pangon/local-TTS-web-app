"""F5-TTS adapter using the ``f5-tts`` package.

Loads ``SWivid/F5-TTS`` via the package's high-level ``f5_tts.api.F5TTS`` class
and runs zero-shot voice-cloning TTS inference locally on GPU.  F5-TTS is a
flow-matching DiT model trained on a 100K-hour multilingual corpus with strong
cross-lingual / code-switching zero-shot ability; output sample rate is 24 kHz
(read from ``model.target_sample_rate`` at load time).

Language handling — **auto-detect variant** (like VoxCPM2, MOSS-TTSD, Fish
S2-Pro and CosyVoice 3, NOT a translate-ISO adapter): the web-verified API
(``F5TTS.infer(ref_file, ref_text, gen_text, …)``) has **no language argument**;
the model infers the spoken language from the reference clip and the generated
text.  ``_resolve_language`` therefore validates the incoming ISO 639-1 code and
defaults it to Italian (``DEC-default-italian-language``) for a clear early
error, but the value is **advisory** — it is not forwarded to the model.

Voice control (important — like CosyVoice 3, F5-TTS has **no built-in
speaker**): synthesis is always zero-shot cloning from a reference clip.
  - ``voice``: path to a reference audio clip (a few seconds of the target
    voice).  ``prompt_text`` (optional): the transcript of that clip; when
    omitted F5-TTS auto-transcribes the reference internally (empty ``ref_text``
    triggers ASR), so a transcript is not required.
  - **Temporary default (until Phase 6 voice selection,**
    ``TASK-voice-language-selection-ui`` **):** when the caller supplies no
    ``voice``, the adapter falls back to a user-provided default clip at
    ``config.DEFAULT_VOICE_PATH`` (the repo-root ``wavs/default.mp3``,
    gitignored) when that file exists — used with empty ``ref_text`` so the clip
    is auto-transcribed.  This is the same stopgap CosyVoice 3 uses so the
    default no-voice creation flow can use this model; once per-request voice
    selection lands it supersedes the default.  If neither a ``voice`` nor the
    default file is present, ``synthesize`` raises a descriptive ``ValueError``
    (the model has no built-in speaker to fall back on).

⚠️ **License: Creative Commons BY-NC 4.0 (weights) — non-commercial / personal
use, NOT FOSS** (the code is MIT, but the model weights are CC-BY-NC; free for
personal/local use, commercial use is not permitted).  Surfaced with a frontend
license notice per ``DEC-model-license-disclosure`` (the metadata is already in
``COMPATIBLE_MODELS`` from Phase 5.2).

.. note::
   **Text normalization.** F5-TTS chunks ``gen_text`` by length and exposes no
   flag to disable internal text handling.  It performs no number/abbreviation
   expansion of its own, so the application's exact user-confirmed, preprocessed
   text (``DEC-preprocess-review-flow``) is spoken essentially verbatim — the
   ``normalize=False`` lever (VoxCPM2/Fish S2-Pro) is therefore not needed.

.. note::
   **Packaging / runtime.** The ``f5-tts`` package pins
   ``numpy<=1.26.4`` on Python ``<=3.10`` (verified against upstream
   ``pyproject.toml``), which conflicts with this backend's baseline (Python
   3.10 with ``numpy`` 2.x, required by ``coqui-tts`` / ``voxcpm``), and it pulls
   a heavy dependency tree (gradio, wandb, bitsandbytes, hydra-core, vocos,
   x_transformers, torchcodec).  Per ``DEC-transformers-5x-baseline`` a package
   that conflicts with the baseline is **not** a backend runtime dependency (it
   must not drive a fresh ``pip install -e .``); it is a **GPU-host
   dependency** — the adapter lazy-imports it at ``load()`` (raising a clear
   install hint if absent), unit tests mock it, and full-weight runtime
   validation is a GPU-host step (the CosyVoice 3 / Fish S2-Pro / Qwen3-TTS
   precedent).  Like those adapters it stays **registered** (registration is
   uniform across GPU-host adapters; loadability is a runtime function of the
   installed environment).  On the GPU host, install it in a dedicated
   environment::

       pip install f5-tts

Decision: DEC-default-italian-language — the default language is Italian.
"""

from __future__ import annotations

import gc
import logging
import re
from typing import Any

import numpy as np
import torch

logger = logging.getLogger(__name__)

# Output sample rate for F5-TTS (24 kHz). Read from ``model.target_sample_rate``
# at load time when available; this is the fallback.
_SAMPLE_RATE_DEFAULT = 24000

# The F5TTS checkpoint variant to load. The package resolves this to
# ``hf://SWivid/F5-TTS/F5TTS_v1_Base/model_*.safetensors`` (the Model Loader has
# already cached the ``SWivid/F5-TTS`` snapshot).
_MODEL_VARIANT = "F5TTS_v1_Base"

# Default language used when none is supplied (DEC-default-italian-language).
# ISO 639-1 code, the convention spoken by the application layer. F5-TTS
# auto-detects the language from the reference clip and text, so this is advisory.
_DEFAULT_LANGUAGE = "it"

# A well-formed ISO 639-1 code is two ASCII letters.
_ISO_639_1_RE = re.compile(r"^[a-z]{2}$")


class F5TTSAdapter:
    """Model adapter for ``SWivid/F5-TTS`` via the ``f5-tts`` package.

    Loads the model with ``f5_tts.api.F5TTS`` (which resolves its checkpoint from
    the cached HuggingFace snapshot downloaded by the Model Loader) and runs
    inference via ``F5TTS.infer`` — always zero-shot cloning from a reference
    clip, since F5-TTS has no built-in speaker.
    """

    def __init__(self) -> None:
        self._model: Any | None = None
        self._device: str | None = None
        self._sample_rate: int = _SAMPLE_RATE_DEFAULT

    def load(self, model_id: str, device: str) -> None:
        """Load F5-TTS onto *device* via the ``f5_tts.api.F5TTS`` class.

        The ``F5TTS`` constructor downloads / resolves its checkpoint from the
        HuggingFace cache (the Model Loader has already fetched the
        ``SWivid/F5-TTS`` snapshot) and selects the given *device* for GPU
        inference (``CON-gpu-inference``).

        Raises:
            RuntimeError: If the ``f5-tts`` package is not installed (it is a
                GPU-host dependency — see the module docstring).
        """
        try:
            from f5_tts.api import F5TTS
        except ImportError as exc:
            raise RuntimeError(
                "The 'f5-tts' package is required for SWivid/F5-TTS but is not "
                "installed. It is a GPU-host dependency (it pins numpy<=1.26.4 on "
                "Python<=3.10 and pulls a heavy dependency tree, so it is not a "
                "backend runtime dependency). Install it in a dedicated "
                "environment on the GPU host:\n"
                "  pip install f5-tts\n"
                f"(original import error: {exc})"
            ) from exc

        logger.info("Loading F5-TTS model %s on %s", model_id, device)
        self._device = device
        self._model = F5TTS(model=_MODEL_VARIANT, device=device)
        self._sample_rate = self._read_sample_rate(self._model)
        logger.info("F5-TTS model loaded successfully (%d Hz)", self._sample_rate)

    def synthesize(self, text: str, **kwargs: Any) -> np.ndarray:
        """Synthesize *text* and return a 1-D float32 numpy array.

        Keyword Args:
            voice: Path to a reference audio clip of the target voice. F5-TTS has
                   no built-in speaker, so a reference is mandatory. When omitted,
                   the adapter falls back to the temporary default clip at
                   ``config.DEFAULT_VOICE_PATH`` (repo-root ``wavs/default.mp3``)
                   if present (Phase-6 stopgap); if that is also absent, a
                   ``ValueError`` is raised.
            prompt_text: Optional transcript of the reference clip. When omitted,
                         F5-TTS auto-transcribes the reference internally (empty
                         ``ref_text`` triggers ASR).
            language: ISO 639-1 code (e.g. ``"it"``, ``"en"``) or ``"auto"``.
                      F5-TTS auto-detects the language, so this value is validated
                      and defaulted to Italian but is **not** forwarded to the
                      model (it is advisory).

        Raises:
            RuntimeError: If called before ``load()``.
            ValueError: If ``language`` is malformed, or if neither a ``voice``
                reference clip nor the temporary default clip is available (the
                model has no built-in speaker).
        """
        if self._model is None:
            raise RuntimeError(
                "F5TTSAdapter.load() must be called before synthesize()"
            )

        # Validate the language for a clear early error, even though the model
        # auto-detects and the value is not forwarded.
        self._resolve_language(kwargs.get("language"))

        ref_file: str | None = kwargs.get("voice") or None
        # F5-TTS auto-transcribes the reference when ref_text is empty, so the
        # transcript is optional.
        ref_text: str = kwargs.get("prompt_text") or ""

        # TEMPORARY (stopgap until Phase 6 voice selection,
        # TASK-voice-language-selection-ui): with no explicit reference, fall back
        # to the user-provided default clip (repo-root wavs/default.mp3) when it
        # exists. It has no transcript, so ref_text stays empty (auto-transcribed).
        if ref_file is None:
            ref_file = self._default_voice_path()
            ref_text = ""

        if ref_file is None:
            raise ValueError(
                "F5-TTS requires a reference voice clip: pass voice=<path to a "
                "few seconds of the target voice>, or place a default clip at "
                "wavs/default.mp3 in the repo root (config.DEFAULT_VOICE_PATH). "
                "The model has no built-in speaker, so it cannot synthesize "
                "without one."
            )

        # F5TTS.infer returns (wav, sample_rate, spectrogram). We keep the audio
        # in memory (no file_wave) and ignore the spectrogram.
        result = self._model.infer(
            ref_file=ref_file,
            ref_text=ref_text,
            gen_text=text,
        )
        return self._extract_wav(result)

    @property
    def sample_rate(self) -> int:
        """The output sample rate of the loaded model in Hz (24 kHz)."""
        return self._sample_rate

    def unload(self) -> None:
        """Release GPU memory held by the F5-TTS model."""
        if self._model is not None:
            del self._model
            self._model = None

        self._device = None

        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()

        logger.info("F5-TTS adapter unloaded")

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _extract_wav(self, result: Any) -> np.ndarray:
        """Coerce ``F5TTS.infer``'s output to a 1-D float32 numpy array.

        ``infer`` returns ``(wav, sample_rate, spectrogram)``; tolerate a bare
        array too. Returns 0.1 s of silence on empty/None output.
        """
        wav = result[0] if isinstance(result, tuple) else result
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
    def _default_voice_path() -> str | None:
        """Return the temporary default reference-clip path if it exists, else None.

        Stopgap until voice selection lands (Phase 6,
        ``TASK-voice-language-selection-ui``): a user-provided clip at
        ``config.DEFAULT_VOICE_PATH`` (repo-root ``wavs/default.mp3``) is used as
        the reference voice when the caller supplies no ``voice``. Read at call
        time so the file can be added/removed without reloading the model.
        """
        from local_tts import config

        path = config.DEFAULT_VOICE_PATH
        return str(path) if path.exists() else None

    @staticmethod
    def _read_sample_rate(model: Any) -> int:
        """Read the output sample rate from the loaded model, with a fallback.

        F5-TTS exposes its output rate as ``model.target_sample_rate`` (24 kHz).
        """
        value = getattr(model, "target_sample_rate", None)
        try:
            if value is not None:
                return int(value)
        except (TypeError, ValueError):
            pass
        return _SAMPLE_RATE_DEFAULT

    @staticmethod
    def _resolve_language(value: str | None) -> str:
        """Validate *value* and resolve it to an ISO 639-1 code.

        F5-TTS auto-detects the spoken language from the reference clip and text,
        so there is no model-specific language identifier to translate to (unlike
        Kokoro or XTTS-v2). This method exists to honour the application's
        ISO-639-1-in convention and to fail clearly on a malformed value rather
        than silently mis-handling it. ``None`` or an empty string falls back to
        the Italian default (``DEC-default-italian-language``); ``"auto"`` is
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
            f"Unsupported language {value!r} for F5-TTS. The model auto-detects "
            f"the language from the reference clip and text; pass an ISO 639-1 "
            f"code (e.g. 'it', 'en') or 'auto'."
        )
