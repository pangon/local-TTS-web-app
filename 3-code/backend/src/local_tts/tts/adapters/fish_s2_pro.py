"""Fish Audio S2-Pro adapter using the ``fish-speech`` package.

Loads ``fishaudio/s2-pro`` via the fish-speech (v2.x) inference engine and runs
TTS inference locally on GPU.  S2-Pro is a Dual-AR model (a 4B "slow" AR for
semantic content + a 400M "fast" AR for acoustic detail) trained on 80+
languages including Italian.  It **auto-detects the language from the input
text** — its request schema (``ServeTTSRequest``) carries no language tag.  Like
VoxCPM2 and MOSS-TTSD (architecture § Adapter Pattern, "auto-detect variant")
the adapter honours the application's ISO-639-1-in convention by validating the
``language`` kwarg and defaulting it to Italian (``DEC-default-italian-language``),
but the value is **advisory** — it is not forwarded to the model.  Voice control
is zero-shot: an optional reference audio clip (with its transcript) clones a
target voice; without one the model uses its default voice.  Output is the
fish-speech DAC sample rate (44.1 kHz), read from the decoder at load time.

⚠️ **License: Fish Audio Research License — non-commercial, NOT FOSS** (free for
personal/local use; commercial use requires a separate license).  Surfaced with
a frontend license notice per ``DEC-model-license-disclosure``.

Decision: DEC-default-italian-language — the default language is Italian.
Decision: DEC-preprocess-review-flow — ``ServeTTSRequest.normalize`` defaults to
``True``, but the application already feeds the exact user-confirmed, preprocessed
text, so this adapter forces ``normalize=False`` to keep that guarantee.

.. note::
   **Packaging / runtime.** ``fish-speech`` v2.0.0 (the S2-Pro–supporting
   release) is **GitHub-only** — PyPI carries only a stale ``0.1.0`` placeholder
   — and it hard-pins ``torch==2.8.0`` and ``transformers<=4.57.3``.  That is
   mutually exclusive with the transformers-5.x models (MOSS-TTSD, Higgs v3),
   with this repo's ``torch>=2.10``, and the model needs 12–24 GB VRAM.  So the
   package is **not** a resolvable runtime dependency here: ``load()``
   lazy-imports it (raising a clear install hint if missing), unit tests mock it,
   and full-weight runtime validation against the real model is a GPU-host step
   (the MOSS-TTSD precedent).  The backend ``transformers`` pin is in an
   exploratory state to permit fish-speech's ``<=4.57.3``
   (``DEC-transformers-5x-baseline``).  On the GPU host, install fish-speech in a
   dedicated environment: ``git clone https://github.com/fishaudio/fish-speech``
   then ``pip install -e .`` (which brings torch 2.8.0 + transformers 4.57.3).
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

# Output sample rate for Fish Audio S2-Pro (fish-speech DAC, 44.1 kHz). The real
# value is read from the loaded decoder model at load time; this is the fallback.
_SAMPLE_RATE_DEFAULT = 44100

# Companion DAC codec weight file inside the model snapshot (per the fish-speech
# S2-Pro inference docs: ``checkpoints/s2-pro/codec.pth``).
_CODEC_FILENAME = "codec.pth"

# fish-speech DAC decoder config name passed to ``load_decoder_model``. This is
# the model's published DAC config; confirm on the GPU host at integration time.
_DECODER_CONFIG_NAME = "modded_dac_vq"

# Default cap on generated semantic tokens per call (mirrors ServeTTSRequest's
# documented default). The synthesizer feeds one preprocessing line per call.
_DEFAULT_MAX_NEW_TOKENS = 1024

# Default language used when none is supplied (DEC-default-italian-language).
# This is an ISO 639-1 code, the convention spoken by the application layer.
# S2-Pro auto-detects the language from the text, so this is advisory only.
_DEFAULT_LANGUAGE = "it"

# A well-formed ISO 639-1 code is two ASCII letters.
_ISO_639_1_RE = re.compile(r"^[a-z]{2}$")


class FishS2ProAdapter:
    """Model adapter for ``fishaudio/s2-pro`` via the ``fish-speech`` package.

    Builds a ``TTSInferenceEngine`` from the model's text2semantic queue and DAC
    decoder, then runs ``engine.inference(ServeTTSRequest(...))`` for synthesis.
    The model auto-detects the input language, so no language identifier is
    passed at inference time; voice is controlled by an optional reference audio
    clip (zero-shot cloning).
    """

    def __init__(self) -> None:
        self._engine: Any | None = None
        self._device: str | None = None
        self._sample_rate: int = _SAMPLE_RATE_DEFAULT

    def load(self, model_id: str, device: str) -> None:
        """Load Fish S2-Pro onto *device* via the fish-speech inference engine.

        Resolves the cached model snapshot (downloaded by the Model Loader),
        launches the text2semantic queue and loads the DAC decoder onto *device*
        for GPU inference (``CON-gpu-inference``), then assembles the
        ``TTSInferenceEngine``.

        Raises:
            RuntimeError: If the ``fish-speech`` package is not installed (it is
                a GPU-host dependency — see the module docstring).
        """
        try:
            from fish_speech.inference_engine import TTSInferenceEngine
            from fish_speech.models.dac.inference import (
                load_model as load_decoder_model,
            )
            from fish_speech.models.text2semantic.inference import (
                launch_thread_safe_queue,
            )
        except ImportError as exc:
            raise RuntimeError(
                "The 'fish-speech' package is required for fishaudio/s2-pro but "
                "is not installed. It is GitHub-only and pins torch==2.8.0 / "
                "transformers<=4.57.3, so install it in a dedicated environment "
                "on the GPU host:\n"
                "  git clone https://github.com/fishaudio/fish-speech\n"
                "  cd fish-speech && pip install -e .\n"
                f"(original import error: {exc})"
            ) from exc

        snapshot_dir = self._resolve_snapshot(model_id)
        precision = torch.bfloat16 if "cuda" in device else torch.float32

        logger.info("Loading Fish S2-Pro model %s on %s", model_id, device)
        self._device = device

        llama_queue = launch_thread_safe_queue(
            checkpoint_path=snapshot_dir,
            device=device,
            precision=precision,
            compile=False,
        )
        decoder_model = load_decoder_model(
            config_name=_DECODER_CONFIG_NAME,
            checkpoint_path=str(Path(snapshot_dir) / _CODEC_FILENAME),
            device=device,
        )
        self._engine = TTSInferenceEngine(
            llama_queue=llama_queue,
            decoder_model=decoder_model,
            precision=precision,
            compile=False,
        )

        self._sample_rate = self._read_sample_rate(decoder_model)
        logger.info(
            "Fish S2-Pro model loaded successfully (%d Hz)", self._sample_rate
        )

    def synthesize(self, text: str, **kwargs: Any) -> np.ndarray:
        """Synthesize *text* and return a 1-D float32 numpy array.

        Keyword Args:
            voice: Optional path to a reference audio clip for zero-shot voice
                   cloning. When omitted, the model uses its default voice.
            prompt_text: Optional transcript of the reference clip; paired with
                         ``voice`` to improve cloning quality.
            language: ISO 639-1 code (e.g. ``"it"``, ``"en"``) or ``"auto"``.
                      S2-Pro auto-detects the language from the text, so this is
                      validated and defaulted to Italian but **not** forwarded.
            max_new_tokens: Cap on generated semantic tokens (default
                            ``_DEFAULT_MAX_NEW_TOKENS``).

        Raises:
            RuntimeError: If called before ``load()`` or if inference errors.
            ValueError: If ``language`` is neither ``"auto"`` nor a well-formed
                ISO 639-1 code.
        """
        if self._engine is None:
            raise RuntimeError(
                "FishS2ProAdapter.load() must be called before synthesize()"
            )

        # Validate the language for a clear early error, even though the model
        # auto-detects and the value is not forwarded.
        self._resolve_language(kwargs.get("language"))

        from fish_speech.utils.schema import ServeTTSRequest

        references = self._build_references(
            kwargs.get("voice") or None, kwargs.get("prompt_text") or None
        )
        request = ServeTTSRequest(
            text=text,
            references=references,
            # The app feeds exact user-confirmed, preprocessed text — never let
            # the model re-normalize it (DEC-preprocess-review-flow).
            normalize=False,
            streaming=False,
            max_new_tokens=int(kwargs.get("max_new_tokens", _DEFAULT_MAX_NEW_TOKENS)),
            format="wav",
        )
        return self._run_inference(request)

    @property
    def sample_rate(self) -> int:
        """The output sample rate of the loaded model in Hz (44.1 kHz)."""
        return self._sample_rate

    def unload(self) -> None:
        """Release GPU memory held by the Fish S2-Pro engine."""
        if self._engine is not None:
            del self._engine
            self._engine = None

        self._device = None

        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()

        logger.info("Fish S2-Pro adapter unloaded")

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _run_inference(self, request: Any) -> np.ndarray:
        """Run inference and return the concatenated waveform.

        ``engine.inference`` yields ``InferenceResult`` objects whose ``code`` is
        one of ``"header"``, ``"segment"``, ``"final"`` or ``"error"`` and whose
        ``audio`` is a ``(sample_rate, numpy_array)`` tuple (or ``None``). The
        audio chunks arrive as ``"segment"`` results; a trailing ``"final"`` may
        repeat the full audio, so segments are preferred and ``"final"`` is only
        used as a fallback to avoid double-counting.
        """
        assert self._engine is not None  # guarded by caller

        segments: list[np.ndarray] = []
        finals: list[np.ndarray] = []
        sample_rate = self._sample_rate

        for result in self._engine.inference(request):
            code = getattr(result, "code", None)
            if code == "error":
                error = getattr(result, "error", None)
                raise RuntimeError(f"Fish S2-Pro inference error: {error}")

            audio = getattr(result, "audio", None)
            if audio is None:
                continue
            rate, samples = audio
            if rate:
                sample_rate = int(rate)
            array = self._to_numpy(samples)
            if array.size == 0:
                continue
            (finals if code == "final" else segments).append(array)

        self._sample_rate = sample_rate
        chosen = segments if segments else finals
        if not chosen:
            return self._silence()
        return np.concatenate(chosen).astype(np.float32)

    @staticmethod
    def _build_references(voice: str | None, prompt_text: str | None) -> list[Any]:
        """Build the reference-audio list for zero-shot cloning, if any.

        Returns an empty list when no ``voice`` clip is supplied (the model then
        uses its default voice).
        """
        if not voice:
            return []
        from fish_speech.utils.schema import ServeReferenceAudio

        audio_bytes = Path(voice).read_bytes()
        return [ServeReferenceAudio(audio=audio_bytes, text=prompt_text or "")]

    @staticmethod
    def _to_numpy(samples: Any) -> np.ndarray:
        """Coerce model audio output to a 1-D float32 numpy array."""
        if isinstance(samples, torch.Tensor):
            samples = samples.detach().cpu().to(torch.float32).numpy()
        return np.asarray(samples, dtype=np.float32).reshape(-1)

    def _silence(self) -> np.ndarray:
        """Return 0.1 s of silence at the model's sample rate."""
        return np.zeros(int(self._sample_rate * 0.1), dtype=np.float32)

    @staticmethod
    def _resolve_snapshot(model_id: str) -> str:
        """Resolve the local path of the cached model snapshot.

        ``snapshot_download`` returns the existing cache path without
        re-downloading when the model is already cached (the Model Loader
        downloads it first). S2-Pro is a gated repo, so the download requires a
        configured HuggingFace token.
        """
        from huggingface_hub import snapshot_download

        return snapshot_download(model_id)

    @staticmethod
    def _read_sample_rate(decoder_model: Any) -> int:
        """Read the DAC output sample rate from the decoder, with a safe default."""
        for attr in ("sample_rate", "sampling_rate"):
            value = getattr(decoder_model, attr, None)
            try:
                if value is not None:
                    return int(value)
            except (TypeError, ValueError):
                pass
        return _SAMPLE_RATE_DEFAULT

    @staticmethod
    def _resolve_language(value: str | None) -> str:
        """Validate *value* and resolve it to an ISO 639-1 code.

        Fish S2-Pro auto-detects the spoken language from the text, so there is
        no model-specific identifier to translate to (unlike Kokoro). This method
        honours the application's ISO-639-1-in convention and fails clearly on a
        malformed value. ``None``/empty falls back to Italian
        (``DEC-default-italian-language``); ``"auto"`` is accepted explicitly.

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
            f"Unsupported language {value!r} for Fish S2-Pro. The model "
            f"auto-detects the language from the text; pass an ISO 639-1 code "
            f"(e.g. 'it', 'en') or 'auto'."
        )
