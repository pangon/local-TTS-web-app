"""Higgs Audio v3 TTS adapter (currently UNREGISTERED — see the note below).

.. warning::
   **This adapter is NOT registered in ``_ADAPTER_REGISTRY`` and the model lists
   with ``loader_available=false`` (verified 2026-06-21).** Boson publishes
   ``bosonai/higgs-audio-v3-tts-4b`` **only as a server** (vLLM-Omni /
   SGLang-Omni; its model card shows no transformers/Python usage). Its
   ``model_type: higgs_multimodal_qwen3`` is **absent from the ``transformers``
   library** (released 5.12.1 *and* ``main``) and the HF repo ships **no remote
   code** (no ``auto_map`` / ``*.py``), so ``trust_remote_code`` cannot help and
   it cannot run **in-process** under ``DEC-single-process``. Attempting to load
   it fails with *"model type ``higgs_multimodal_qwen3`` ... does not recognize
   this architecture."* Supporting v3 would require a server-backed loader
   (rejected for now — `DEC-single-process`).

   This module is **retained on the bet that ``transformers`` later adds native
   ``higgs_multimodal_qwen3`` support**, at which point the pipeline-based load
   path below should work and the adapter can simply be re-registered. The
   implementation and its unit tests are kept (the tests mock ``pipeline``, so
   they validate the adapter's logic, not that the model is actually runnable).

The intended (future) approach, were the architecture available in transformers:
Higgs Audio v3 is a text-audio foundation model (a Qwen3-4B backbone) whose audio
is decoded internally from 8 interleaved codebooks (delay-pattern). The adapter
would use the high-level transformers ``text-to-speech`` pipeline — owning the
processor → ``generate`` → codec-decode sequence and returning a waveform plus
sample rate — to keep inference in-process (``DEC-single-process`` /
``CON-gpu-inference``) rather than via Boson's SGLang-Omni / vLLM-Omni servers.

Language: Higgs Audio v3 supports 100+ languages (incl. Italian) and **detects
the language from the input text** — no documented local-inference path
(``pipeline("text-to-speech")`` / ``AutoModelForSeq2SeqLM``, or the server
``/v1/audio/speech`` API) takes a language tag.  Like VoxCPM2, MOSS-TTSD and
Fish S2-Pro (architecture § Adapter Pattern, "auto-detect variant") this adapter
honours the application's ISO-639-1-in convention by validating the ``language``
kwarg and defaulting it to Italian (``DEC-default-italian-language``), but the
value is **advisory** — it is not forwarded to the model.  Voice control is
zero-shot: an optional reference audio clip (with its transcript) clones a
target voice; without one the model uses its default voice.  Output is 24 kHz,
read from the pipeline at load time.

⚠️ **License: Boson Higgs Audio v3 Research and Non-Commercial License — NOT
FOSS** (free for research / personal / non-commercial use; production, hosted
APIs or revenue-generating use require a separate paid license).  Surfaced with
a frontend license notice per ``DEC-model-license-disclosure``.

Decision: DEC-default-italian-language — the default language is Italian.
Decision: DEC-preprocess-review-flow — the exact user-confirmed, preprocessed
text is fed to the model unchanged (the TTS pipeline performs no extra text
normalization beyond the model's own tokenization).

The adapter module imports cleanly on any transformers (``pipeline`` has existed
since early transformers and importing it loads no weights), so keeping it on
disk costs nothing even while unregistered.
"""

from __future__ import annotations

import gc
import logging
import re
from typing import Any

import numpy as np
import torch
from transformers import pipeline

logger = logging.getLogger(__name__)

# transformers pipeline task for text-to-audio synthesis.
_TTS_TASK = "text-to-speech"

# Output sample rate for Higgs Audio v3 (24 kHz). The real value is read from
# the loaded pipeline at load time; this is the fallback.
_SAMPLE_RATE_DEFAULT = 24000

# Default cap on generated audio tokens per call. The synthesizer feeds one
# preprocessing line (sentence) per call; the audio decoder runs at 25 fps, so
# this is ample headroom for a single sentence.
_DEFAULT_MAX_NEW_TOKENS = 2048

# Default language used when none is supplied (DEC-default-italian-language).
# This is an ISO 639-1 code, the convention spoken by the application layer.
# Higgs Audio v3 auto-detects the language from the text, so this is advisory.
_DEFAULT_LANGUAGE = "it"

# A well-formed ISO 639-1 code is two ASCII letters.
_ISO_639_1_RE = re.compile(r"^[a-z]{2}$")


class HiggsAudioV3Adapter:
    """Model adapter for ``bosonai/higgs-audio-v3-tts-4b``.

    Loads the model via the transformers ``text-to-speech`` pipeline (the
    architecture would be native in transformers — it is not yet, so the adapter
    is unregistered; see the module docstring) and runs synthesis by calling the
    pipeline, which returns ``{"audio": ndarray, "sampling_rate": int}``. The
    model auto-detects the input language, so no language identifier is passed at
    inference time; voice is controlled by an optional reference audio clip
    (zero-shot cloning).
    """

    def __init__(self) -> None:
        self._pipe: Any | None = None
        self._device: str | None = None
        self._sample_rate: int = _SAMPLE_RATE_DEFAULT

    def load(self, model_id: str, device: str) -> None:
        """Load Higgs Audio v3 onto *device* via the transformers TTS pipeline.

        .. warning::
           This currently FAILS: ``higgs_multimodal_qwen3`` is not in the
           ``transformers`` library and the repo ships no remote code, so the
           pipeline build raises *"does not recognize this architecture"*. The
           adapter is unregistered for this reason (see the module docstring);
           this path is retained for if/when transformers adds native support.

        The model weights are downloaded/cached by the Model Loader; the
        pipeline would be built on *device* for GPU inference
        (``CON-gpu-inference``) with bfloat16 precision on CUDA.

        Raises:
            RuntimeError: Currently always (the architecture is unavailable in
                transformers — Higgs v3 is published server-only). The wrapped
                error explains the cause; see ``DEC-single-process``.
        """
        logger.info("Loading Higgs Audio v3 model %s on %s", model_id, device)
        self._device = device

        dtype = torch.bfloat16 if "cuda" in device else torch.float32
        try:
            self._pipe = pipeline(
                _TTS_TASK,
                model=model_id,
                device=device,
                torch_dtype=dtype,
            )
        except Exception as exc:  # pragma: no cover - exercised on the GPU host
            raise RuntimeError(
                f"Failed to load Higgs Audio v3 ({model_id}). Its architecture "
                "'higgs_multimodal_qwen3' is not implemented in the transformers "
                "library (released or main) and the model ships no remote code, "
                "so it cannot be loaded in-process. Boson publishes v3 only as a "
                "vLLM-Omni / SGLang-Omni server, which is out of scope for this "
                "in-process app (DEC-single-process). "
                f"(original error: {exc})"
            ) from exc

        self._sample_rate = self._read_sample_rate(self._pipe)
        logger.info(
            "Higgs Audio v3 model loaded successfully (%d Hz)", self._sample_rate
        )

    def synthesize(self, text: str, **kwargs: Any) -> np.ndarray:
        """Synthesize *text* and return a 1-D float32 numpy array.

        Keyword Args:
            voice: Optional path to a reference audio clip for zero-shot voice
                   cloning. When omitted, the model uses its default voice.
            prompt_text: Optional transcript of the reference clip; paired with
                         ``voice`` to materially improve cloning fidelity.
            language: ISO 639-1 code (e.g. ``"it"``, ``"en"``) or ``"auto"``.
                      Higgs Audio v3 auto-detects the language from the text, so
                      this value is validated and defaulted to Italian but is
                      **not** forwarded to the model (it is advisory).
            max_new_tokens: Cap on generated audio tokens (default
                            ``_DEFAULT_MAX_NEW_TOKENS``).

        Raises:
            RuntimeError: If called before ``load()``.
            ValueError: If ``language`` is neither ``"auto"`` nor a well-formed
                ISO 639-1 code.
        """
        if self._pipe is None:
            raise RuntimeError(
                "HiggsAudioV3Adapter.load() must be called before synthesize()"
            )

        # Validate the language for a clear early error, even though the model
        # auto-detects and the value is not forwarded.
        self._resolve_language(kwargs.get("language"))

        call_kwargs = self._build_call_kwargs(kwargs)
        output = self._pipe(text, **call_kwargs)
        return self._coerce_output(output)

    @property
    def sample_rate(self) -> int:
        """The output sample rate of the loaded model in Hz (24 kHz)."""
        return self._sample_rate

    def unload(self) -> None:
        """Release GPU memory held by the Higgs Audio v3 pipeline."""
        if self._pipe is not None:
            del self._pipe
            self._pipe = None

        self._device = None

        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()

        logger.info("Higgs Audio v3 adapter unloaded")

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _build_call_kwargs(self, kwargs: dict[str, Any]) -> dict[str, Any]:
        """Assemble the keyword arguments for the pipeline call.

        ``generate_kwargs`` caps the generated audio tokens.  An optional
        reference clip enables zero-shot voice cloning and is passed via
        ``forward_params`` using the model's documented reference inputs
        (``reference_audio`` + ``reference_text``); the exact wiring of the
        reference into the native pipeline is confirmed on the GPU host (the
        default-voice path needs no reference and is the primary one).
        """
        max_new_tokens = int(kwargs.get("max_new_tokens", _DEFAULT_MAX_NEW_TOKENS))
        call_kwargs: dict[str, Any] = {
            "generate_kwargs": {"max_new_tokens": max_new_tokens},
        }

        voice = kwargs.get("voice") or None
        if voice:
            call_kwargs["forward_params"] = {
                "reference_audio": voice,
                "reference_text": kwargs.get("prompt_text") or "",
            }
        return call_kwargs

    def _coerce_output(self, output: Any) -> np.ndarray:
        """Coerce a TTS-pipeline result to a 1-D float32 numpy array.

        The transformers ``text-to-speech`` pipeline returns a dict (or a
        single-element list of dicts for batch size 1) with an ``"audio"``
        waveform and a ``"sampling_rate"``.  The real sample rate is captured
        when present.  Returns a short silence when the model produced nothing.
        """
        if isinstance(output, list):
            output = output[0] if output else None
        if output is None:
            return self._silence()

        rate = None
        audio: Any = output
        if isinstance(output, dict):
            audio = output.get("audio")
            rate = output.get("sampling_rate")

        if rate:
            try:
                self._sample_rate = int(rate)
            except (TypeError, ValueError):
                pass

        if audio is None:
            return self._silence()

        if isinstance(audio, torch.Tensor):
            audio = audio.detach().cpu().to(torch.float32).numpy()

        waveform = np.asarray(audio, dtype=np.float32).reshape(-1)
        if waveform.size == 0:
            return self._silence()
        return waveform

    def _silence(self) -> np.ndarray:
        """Return 0.1 s of silence at the model's sample rate."""
        return np.zeros(int(self._sample_rate * 0.1), dtype=np.float32)

    @staticmethod
    def _read_sample_rate(pipe: Any) -> int:
        """Read the output sample rate from the pipeline, with a safe default.

        The transformers ``TextToAudioPipeline`` exposes ``sampling_rate``;
        fall back to the model config and finally the 24 kHz default.
        """
        rate = getattr(pipe, "sampling_rate", None)
        if rate is None:
            config = getattr(getattr(pipe, "model", None), "config", None)
            for attr in ("sampling_rate", "sample_rate", "audio_sample_rate"):
                value = getattr(config, attr, None)
                if value is not None:
                    rate = value
                    break
        try:
            if rate is not None:
                return int(rate)
        except (TypeError, ValueError):
            pass
        return _SAMPLE_RATE_DEFAULT

    @staticmethod
    def _resolve_language(value: str | None) -> str:
        """Validate *value* and resolve it to an ISO 639-1 code.

        Higgs Audio v3 auto-detects the spoken language from the text, so there
        is no model-specific identifier to translate to (unlike Kokoro). This
        method honours the application's ISO-639-1-in convention and fails
        clearly on a malformed value. ``None``/empty falls back to Italian
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
            f"Unsupported language {value!r} for Higgs Audio v3. The model "
            f"auto-detects the language from the text; pass an ISO 639-1 code "
            f"(e.g. 'it', 'en') or 'auto'."
        )
