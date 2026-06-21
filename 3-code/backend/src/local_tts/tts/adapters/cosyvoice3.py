"""CosyVoice 3 adapter using the FunAudioLLM ``cosyvoice`` package.

Loads ``FunAudioLLM/Fun-CosyVoice3-0.5B-2512`` via the CosyVoice package's own
``AutoModel`` (``cosyvoice.cli.cosyvoice.AutoModel`` — **not** HuggingFace's
``AutoModel``) from the HuggingFace-cached snapshot and runs multilingual TTS
inference locally on GPU.  CosyVoice 3 is a zero-shot voice-cloning model that
**auto-detects the spoken language from the input text** — it takes no language
tag (the documented ``<|zh|>``/``<|en|>``… tags cover only a handful of
languages; Italian is handled by auto-detection).  Output sample rate is 24 kHz
(read from ``model.sample_rate`` at load time).

This is an **auto-detect language variant** like VoxCPM2, MOSS-TTSD and Fish
S2-Pro — NOT a translate-ISO adapter (the task description's "translate ISO →
identifier" wording did not match the web-verified API; the model card shows no
per-call language argument).  ``_resolve_language`` therefore validates the
incoming ISO 639-1 code and defaults it to Italian
(``DEC-default-italian-language``) for a clear early error, but the value is
**advisory** — it is not forwarded to the model.

Voice control (important — differs from every prior adapter):
  - CosyVoice 3 has **no built-in / SFT speaker** (the model snapshot ships no
    ``spk2info.pt`` and no bundled reference clip), so it **cannot synthesize
    without a reference voice clip**.  A reference clip is supplied via the
    ``voice`` kwarg (a path to a ``.wav``/``.mp3`` of 3–10 s of the target
    voice); with an optional ``prompt_text`` transcript it uses zero-shot
    cloning, otherwise cross-lingual cloning.
  - **Temporary default (until Phase 6 voice selection,**
    ``TASK-voice-language-selection-ui`` **):** when the caller supplies no
    ``voice``, the adapter falls back to a user-provided default clip at
    ``config.DEFAULT_VOICE_PATH`` (the repo-root ``wavs/default.mp3``, gitignored)
    when that file exists — used via cross-lingual cloning (no transcript), so
    its timbre is applied to Italian text.  This is a stopgap so the default
    no-voice creation flow can use this model; once per-request voice selection
    lands it supersedes the default.  If neither a ``voice`` nor the default file
    is present, ``synthesize`` raises a descriptive ``ValueError`` (the model has
    no built-in speaker to fall back on).

⚠️ **License: Apache-2.0 (FOSS)** — no usage caveat.

.. note::
   **Packaging / runtime.** The ``cosyvoice`` package hard-pins
   ``transformers==4.51.3``, ``torch==2.3.1`` and ``numpy==1.26.4`` (verified
   against the upstream ``requirements.txt``), which conflict with this
   backend's baseline.  Per ``DEC-transformers-5x-baseline`` a package that
   hard-pins ``transformers``/``torch`` is **not** a backend runtime dependency
   (it must not drive a fresh ``pip install -e .``); it is a **GPU-host
   dependency**.  The adapter therefore lazy-imports it at ``load()`` (raising a
   clear install hint if absent), unit tests mock it, and full-weight runtime
   validation is a GPU-host step (the Qwen3-TTS / Fish S2-Pro precedent).  Like
   those adapters it stays **registered** (registration is uniform across
   GPU-host adapters; loadability is a runtime function of the installed
   environment).  On the GPU host, install it in a dedicated environment from
   the CosyVoice repo, e.g.::

       git clone --recursive https://github.com/FunAudioLLM/CosyVoice.git
       cd CosyVoice && pip install -r requirements.txt
       # (the package adds third_party/Matcha-TTS to sys.path)

Decision: DEC-default-italian-language — the default language is Italian.
"""

from __future__ import annotations

import gc
import logging
import re
from pathlib import Path
from typing import Any

import numpy as np
import torch

logger = logging.getLogger(__name__)

# Output sample rate for CosyVoice 3 (24 kHz). Read from ``model.sample_rate``
# at load time when available; this is the fallback.
_SAMPLE_RATE_DEFAULT = 24000

# Default language used when none is supplied (DEC-default-italian-language).
# ISO 639-1 code, the convention spoken by the application layer. CosyVoice 3
# auto-detects the language from the text, so this is advisory only.
_DEFAULT_LANGUAGE = "it"

# A well-formed ISO 639-1 code is two ASCII letters.
_ISO_639_1_RE = re.compile(r"^[a-z]{2}$")


class CosyVoice3Adapter:
    """Model adapter for ``FunAudioLLM/Fun-CosyVoice3-0.5B-2512``.

    Loads the model with the CosyVoice package's ``AutoModel`` from the cached
    HuggingFace snapshot (downloaded by the Model Loader) and runs inference via
    ``inference_zero_shot`` / ``inference_cross_lingual`` — both of which require
    a reference voice clip (CosyVoice 3 has no built-in speaker).
    """

    def __init__(self) -> None:
        self._model: Any | None = None
        self._device: str | None = None
        self._sample_rate: int = _SAMPLE_RATE_DEFAULT

    def load(self, model_id: str, device: str) -> None:
        """Load CosyVoice 3 onto *device* via the package's ``AutoModel``.

        Resolves the cached model snapshot (downloaded by the Model Loader) and
        instantiates ``AutoModel(model_dir=…)``; CosyVoice selects CUDA
        automatically when available (``CON-gpu-inference``).

        Raises:
            RuntimeError: If the ``cosyvoice`` package is not installed (it is a
                GPU-host dependency — see the module docstring).
        """
        try:
            from cosyvoice.cli.cosyvoice import AutoModel
        except ImportError as exc:
            raise RuntimeError(
                "The 'cosyvoice' package is required for "
                "FunAudioLLM/Fun-CosyVoice3-0.5B-2512 but is not installed. It is "
                "a GPU-host dependency (it hard-pins transformers==4.51.3 / "
                "torch==2.3.1, so it is not a backend runtime dependency). Install "
                "it from the CosyVoice repo in a dedicated environment:\n"
                "  git clone --recursive https://github.com/FunAudioLLM/CosyVoice.git\n"
                "  cd CosyVoice && pip install -r requirements.txt\n"
                f"(original import error: {exc})"
            ) from exc

        snapshot_dir = self._resolve_snapshot(model_id)

        logger.info("Loading CosyVoice 3 model %s on %s", model_id, device)
        self._device = device
        self._model = AutoModel(model_dir=snapshot_dir)
        self._sample_rate = self._read_sample_rate(self._model)
        logger.info(
            "CosyVoice 3 model loaded successfully (%d Hz)", self._sample_rate
        )

    def synthesize(self, text: str, **kwargs: Any) -> np.ndarray:
        """Synthesize *text* and return a 1-D float32 numpy array.

        Keyword Args:
            voice: Path to a reference audio clip (3–10 s ``.wav``/``.mp3``) for
                   zero-shot voice cloning. CosyVoice 3 has no built-in speaker.
                   When omitted, the adapter falls back to the temporary default
                   clip at ``config.DEFAULT_VOICE_PATH`` (repo-root
                   ``wavs/default.mp3``) if present (Phase-6 stopgap); if that is
                   also absent, a ``ValueError`` is raised.
            prompt_text: Optional transcript of the reference clip. When given,
                         zero-shot cloning (``inference_zero_shot``) is used;
                         otherwise cross-lingual cloning
                         (``inference_cross_lingual``).
            language: ISO 639-1 code (e.g. ``"it"``, ``"en"``) or ``"auto"``.
                      CosyVoice 3 auto-detects the language from the text, so this
                      value is validated and defaulted to Italian but is **not**
                      forwarded to the model (it is advisory).

        Raises:
            RuntimeError: If called before ``load()``.
            ValueError: If ``language`` is malformed, or if neither a ``voice``
                reference clip nor the temporary default clip is available (the
                model has no built-in speaker).
        """
        if self._model is None:
            raise RuntimeError(
                "CosyVoice3Adapter.load() must be called before synthesize()"
            )

        # Validate the language for a clear early error, even though the model
        # auto-detects and the value is not forwarded.
        self._resolve_language(kwargs.get("language"))

        prompt_wav_path: str | None = kwargs.get("voice") or None
        prompt_text: str | None = kwargs.get("prompt_text") or None

        # TEMPORARY (stopgap until Phase 6 voice selection,
        # TASK-voice-language-selection-ui): with no explicit reference, fall back
        # to the user-provided default clip (repo-root wavs/default.mp3) when it
        # exists. It has no transcript, so cross-lingual cloning is used below.
        if prompt_wav_path is None:
            prompt_wav_path = self._default_voice_path()
            prompt_text = None

        if prompt_wav_path is None:
            raise ValueError(
                "CosyVoice 3 requires a reference voice clip: pass voice=<path to "
                "a 3-10 s .wav/.mp3 of the target voice>, or place a default clip "
                "at wavs/default.mp3 in the repo root (config.DEFAULT_VOICE_PATH). "
                "The model has no built-in speaker, so it cannot synthesize "
                "without one."
            )

        # zero-shot needs a transcript of the reference; cross-lingual does not.
        # Both auto-detect the target language from `text` and yield a generator
        # of {"tts_speech": <tensor>} chunks (stream=False → the full audio).
        if prompt_text is not None:
            generator = self._model.inference_zero_shot(
                text, prompt_text, prompt_wav_path, stream=False
            )
        else:
            generator = self._model.inference_cross_lingual(
                text, prompt_wav_path, stream=False
            )

        return self._collect_audio(generator)

    @property
    def sample_rate(self) -> int:
        """The output sample rate of the loaded model in Hz (24 kHz)."""
        return self._sample_rate

    def unload(self) -> None:
        """Release GPU memory held by the CosyVoice 3 model."""
        if self._model is not None:
            del self._model
            self._model = None

        self._device = None

        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()

        logger.info("CosyVoice 3 adapter unloaded")

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _collect_audio(self, generator: Any) -> np.ndarray:
        """Concatenate the ``tts_speech`` chunks from an inference generator.

        CosyVoice inference methods return a generator yielding
        ``{"tts_speech": <tensor>}`` dicts. Collect every chunk, coerce to a 1-D
        float32 array, and concatenate. Returns 0.1 s of silence when the model
        yields nothing usable.
        """
        chunks: list[np.ndarray] = []
        for out in generator:
            speech = out.get("tts_speech") if isinstance(out, dict) else out
            if speech is None:
                continue
            audio = self._to_numpy(speech)
            if audio.size:
                chunks.append(audio)

        if not chunks:
            return self._silence()
        return np.concatenate(chunks)

    @staticmethod
    def _to_numpy(speech: Any) -> np.ndarray:
        """Coerce a model speech chunk to a 1-D float32 numpy array."""
        if isinstance(speech, torch.Tensor):
            speech = speech.detach().cpu().to(torch.float32).numpy()
        return np.asarray(speech, dtype=np.float32).reshape(-1)

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
    def _resolve_snapshot(model_id: str) -> str:
        """Resolve the local path of the cached model snapshot.

        ``snapshot_download`` returns the existing cache path without
        re-downloading when the model is already cached (the Model Loader
        downloads it first).
        """
        from huggingface_hub import snapshot_download

        return snapshot_download(model_id)

    @staticmethod
    def _read_sample_rate(model: Any) -> int:
        """Read the output sample rate from the loaded model, with a fallback.

        CosyVoice exposes its output rate as ``model.sample_rate`` (24 kHz for
        CosyVoice 3).
        """
        value = getattr(model, "sample_rate", None)
        try:
            if value is not None:
                return int(value)
        except (TypeError, ValueError):
            pass
        return _SAMPLE_RATE_DEFAULT

    @staticmethod
    def _resolve_language(value: str | None) -> str:
        """Validate *value* and resolve it to an ISO 639-1 code.

        CosyVoice 3 auto-detects the spoken language from the text, so there is
        no model-specific language identifier to translate to (unlike Kokoro or
        Qwen3-TTS). This method exists to honour the application's ISO-639-1-in
        convention and to fail clearly on a malformed value rather than silently
        mis-handling it. ``None`` or an empty string falls back to the Italian
        default (``DEC-default-italian-language``); ``"auto"`` is accepted
        explicitly.

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
            f"Unsupported language {value!r} for CosyVoice 3. The model "
            f"auto-detects the language from the text; pass an ISO 639-1 code "
            f"(e.g. 'it', 'en') or 'auto'."
        )
