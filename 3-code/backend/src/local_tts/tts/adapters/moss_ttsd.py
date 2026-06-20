"""MOSS-TTSD v1.0 adapter using transformers ``trust_remote_code`` loading.

Loads ``OpenMOSS-Team/MOSS-TTSD-v1.0`` via ``AutoProcessor`` / ``AutoModel``
with ``trust_remote_code=True`` (the model ships its own processing and
modeling code) plus the companion audio tokenizer
``OpenMOSS-Team/MOSS-Audio-Tokenizer``, and runs TTS inference locally on GPU.

MOSS-TTSD is a spoken-**dialogue** model designed for expressive
multi-speaker synthesis (1–5 speakers tagged ``[S1]`` … ``[S5]``) with
zero-shot voice cloning from short reference clips.  Using it for the app's
single-voice audiobook narration is a recognised architectural mismatch
(architecture § Model-Specific Loading Requirements): this adapter wraps the
input in a single ``[S1]`` speaker turn and, by default, generates without a
reference clip (the model picks its own voice).  An optional reference clip
(``voice``) plus its transcript (``prompt_text``) enables zero-shot cloning.

Language: MOSS-TTSD **auto-detects** the spoken language from the input text —
the inference API takes no language tag (20 languages incl. Italian).  Like
VoxCPM2 (architecture § Adapter Pattern, "auto-detect variant") the adapter
honours the application's ISO-639-1-in convention by validating the
``language`` kwarg and defaulting it to Italian
(``DEC-default-italian-language``), but the value is **advisory** — it is not
forwarded to the model.

Decision: DEC-default-italian-language — the default language is Italian.
Decision: DEC-preprocess-review-flow — the exact user-confirmed, preprocessed
text is fed to the model unchanged (the model exposes no text-normalizer
toggle to disable).

.. note::
   The inference call sequence mirrors the model's published
   ``AutoModel``/``AutoProcessor`` continuation workflow.  The package is not
   installed in this environment (the ~8B model is ~19 GB and exceeds the
   min-spec 4 GB GPU), so unit tests mock it; runtime validation against the
   real weights is performed on a GPU host.
"""

from __future__ import annotations

import gc
import logging
import re
from typing import Any

import numpy as np
import torch

logger = logging.getLogger(__name__)

# Output sample rate for MOSS-TTSD (24 kHz). The real value is read from the
# processor's ``model_config.sampling_rate`` at load time; this is the fallback.
_SAMPLE_RATE_DEFAULT = 24000

# Companion audio tokenizer (codec) required by the processor.
_AUDIO_TOKENIZER_ID = "OpenMOSS-Team/MOSS-Audio-Tokenizer"

# Pinned model repo revision (HuggingFace commit). ``trust_remote_code`` pulls
# the model's own Python from the repo; without a pin it silently tracks the
# repo HEAD, which can introduce a newer-transformers requirement and break
# loading (the architecture § Model-Specific Loading Requirements recommends
# pinning a revision). This commit's remote code is compatible with the
# transformers version this project pins.
_MODEL_REVISION = "c7cd852d87aff71cab5bd2b9b05509cedc0ef1ba"

# Default language used when none is supplied (DEC-default-italian-language).
# This is an ISO 639-1 code, the convention spoken by the application layer.
# MOSS-TTSD auto-detects the language from the text, so this is advisory only.
_DEFAULT_LANGUAGE = "it"

# A well-formed ISO 639-1 code is two ASCII letters.
_ISO_639_1_RE = re.compile(r"^[a-z]{2}$")

# Speaker tag used to wrap single-voice narration text. MOSS-TTSD expects
# turns tagged ``[S1]`` … ``[S5]``; single-speaker narration uses ``[S1]``.
_SINGLE_SPEAKER_TAG = "[S1]"

# Detects whether the text already opens with a speaker tag, so we do not
# double-wrap caller-supplied dialogue markup.
_SPEAKER_TAG_RE = re.compile(r"^\s*\[S[1-5]\]")

# Default cap on generated audio tokens per call. The synthesizer feeds one
# preprocessing line (sentence) per call, so this is ample headroom.
_DEFAULT_MAX_NEW_TOKENS = 2000


def _install_transformers_compat() -> None:
    """Bridge the transformers 5.x ``PretrainedConfig`` → ``PreTrainedConfig`` rename.

    MOSS-TTSD's companion audio tokenizer (``OpenMOSS-Team/MOSS-Audio-Tokenizer``,
    loaded via ``codec_path``) imports ``PreTrainedConfig`` — the name introduced
    when transformers 5.x renamed ``PretrainedConfig`` (the same class). On
    transformers 4.x that new name is absent, so the codec's ``trust_remote_code``
    import fails with ``cannot import name 'PreTrainedConfig'``. This idempotently
    aliases the new name onto the existing class so the remote code loads.

    The project baseline is transformers 5.x (``DEC-transformers-5x-baseline``,
    required because the MOSS-TTSD model code also imports the 5.x
    ``transformers.initialization`` module), where ``PreTrainedConfig`` already
    exists — so this shim is a **defensive no-op** there, kept only to fail
    gracefully if the adapter is ever run on an older transformers.
    """
    import transformers
    from transformers import configuration_utils

    if not hasattr(configuration_utils, "PreTrainedConfig") and hasattr(
        configuration_utils, "PretrainedConfig"
    ):
        configuration_utils.PreTrainedConfig = configuration_utils.PretrainedConfig
        # Some remote code imports the name from the top-level package too.
        if not hasattr(transformers, "PreTrainedConfig"):
            transformers.PreTrainedConfig = configuration_utils.PretrainedConfig


class MOSSTTSDAdapter:
    """Model adapter for ``OpenMOSS-Team/MOSS-TTSD-v1.0``.

    Loads the model and its processor via transformers ``trust_remote_code``
    and runs the published continuation-style generation workflow.  The input
    text is wrapped as a single ``[S1]`` speaker turn (single-voice narration);
    an optional reference clip enables zero-shot voice cloning.
    """

    def __init__(self) -> None:
        self._model: Any | None = None
        self._processor: Any | None = None
        self._device: str | None = None
        self._sample_rate: int = _SAMPLE_RATE_DEFAULT

    def load(self, model_id: str, device: str) -> None:
        """Load MOSS-TTSD onto *device* via ``AutoProcessor`` / ``AutoModel``.

        The processor is built with ``trust_remote_code=True`` and the
        companion audio tokenizer (``codec_path``); the model is loaded with
        ``trust_remote_code=True`` and moved to *device* for GPU inference
        (``CON-gpu-inference``).  FlashAttention 2 is used when available,
        falling back to the memory-efficient ``sdpa`` implementation. Both
        ``from_pretrained`` calls pin ``_MODEL_REVISION`` so the remote code is
        stable, and the transformers 5.x ``PreTrainedConfig`` rename is bridged
        for the codec via ``_install_transformers_compat`` first.
        """
        # Bridge the transformers 5.x config-class rename before any remote code
        # (model or codec) is imported, otherwise the codec import fails on 4.x.
        _install_transformers_compat()

        from transformers import AutoModel, AutoProcessor

        logger.info("Loading MOSS-TTSD model %s on %s", model_id, device)
        self._device = device

        dtype = torch.bfloat16 if "cuda" in device else torch.float32
        attn_impl = self._detect_attn_implementation()

        processor = AutoProcessor.from_pretrained(
            model_id,
            revision=_MODEL_REVISION,
            trust_remote_code=True,
            codec_path=_AUDIO_TOKENIZER_ID,
        )
        # The audio tokenizer (codec) must run on the same device as the model.
        if hasattr(processor, "audio_tokenizer") and processor.audio_tokenizer is not None:
            processor.audio_tokenizer = processor.audio_tokenizer.to(device)
        self._processor = processor

        model = AutoModel.from_pretrained(
            model_id,
            revision=_MODEL_REVISION,
            trust_remote_code=True,
            attn_implementation=attn_impl,
            torch_dtype=dtype,
        ).to(device)
        model.eval()
        self._model = model

        self._sample_rate = self._read_sample_rate(processor)
        logger.info(
            "MOSS-TTSD model loaded successfully (%d Hz)", self._sample_rate
        )

    def synthesize(self, text: str, **kwargs: Any) -> np.ndarray:
        """Synthesize *text* and return a 1-D float32 numpy array.

        Keyword Args:
            voice: Optional path to a reference audio clip for zero-shot voice
                   cloning.  When omitted, the model generates with its own
                   voice (single-voice narration — the dialogue-model mismatch
                   noted above).
            prompt_text: Optional transcript of the reference clip; used with
                         ``voice`` to anchor the cloned voice.
            language: ISO 639-1 code (e.g. ``"it"``, ``"en"``) or ``"auto"``.
                      MOSS-TTSD auto-detects the language from the text, so this
                      value is validated and defaulted to Italian but is **not**
                      forwarded to the model (it is advisory).
            max_new_tokens: Cap on generated audio tokens (model default used
                            via ``_DEFAULT_MAX_NEW_TOKENS`` when omitted).

        Raises:
            RuntimeError: If called before ``load()``.
            ValueError: If ``language`` is neither ``"auto"`` nor a well-formed
                ISO 639-1 code.
        """
        if self._model is None or self._processor is None:
            raise RuntimeError(
                "MOSSTTSDAdapter.load() must be called before synthesize()"
            )

        # Validate the language for a clear early error, even though the model
        # auto-detects and the value is not forwarded.
        self._resolve_language(kwargs.get("language"))

        reference_wav: str | None = kwargs.get("voice") or None
        prompt_text: str | None = kwargs.get("prompt_text") or None
        max_new_tokens = int(kwargs.get("max_new_tokens", _DEFAULT_MAX_NEW_TOKENS))

        dialogue_text = self._as_single_speaker(text)

        raw_audio = self._generate(
            dialogue_text=dialogue_text,
            reference_wav=reference_wav,
            prompt_text=prompt_text,
            max_new_tokens=max_new_tokens,
        )
        return self._coerce_waveform(raw_audio)

    @property
    def sample_rate(self) -> int:
        """The output sample rate of the loaded model in Hz (24 kHz)."""
        return self._sample_rate

    def unload(self) -> None:
        """Release GPU memory held by the MOSS-TTSD model and processor."""
        if self._model is not None:
            del self._model
            self._model = None

        if self._processor is not None:
            del self._processor
            self._processor = None

        self._device = None

        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()

        logger.info("MOSS-TTSD adapter unloaded")

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _generate(
        self,
        dialogue_text: str,
        reference_wav: str | None,
        prompt_text: str | None,
        max_new_tokens: int,
    ) -> Any:
        """Run the continuation-style generation workflow and return raw audio.

        Mirrors the published ``AutoProcessor`` / ``AutoModel`` example: build a
        conversation (user message + optional reference/assistant prompt),
        construct the batch in ``continuation`` mode, generate, and decode the
        first speaker turn's waveform.
        """
        processor = self._processor
        model = self._model
        assert processor is not None and model is not None  # guarded by caller

        if reference_wav:
            reference_codes = processor.encode_audios_from_wav(
                [reference_wav],
                sampling_rate=int(self._sample_rate),
            )
            user_text = dialogue_text
            if prompt_text:
                user_text = f"{self._as_single_speaker(prompt_text)} {dialogue_text}"
            conversation = [
                processor.build_user_message(
                    text=user_text, reference=reference_codes
                ),
                processor.build_assistant_message(
                    audio_codes_list=reference_codes
                ),
            ]
        else:
            conversation = [
                processor.build_user_message(text=dialogue_text, reference=None),
            ]

        batch = processor([conversation], mode="continuation")
        if hasattr(batch, "to") and self._device is not None:
            batch = batch.to(self._device)

        gen_kwargs: dict[str, Any] = {"max_new_tokens": max_new_tokens}
        for key in ("input_ids", "attention_mask"):
            if key in batch:
                gen_kwargs[key] = batch[key]

        with torch.no_grad():
            outputs = model.generate(**gen_kwargs)

        decoded = processor.decode(outputs)
        return self._extract_first_audio(decoded)

    @staticmethod
    def _extract_first_audio(decoded: Any) -> Any:
        """Return the first speaker turn's waveform from a decoded result.

        ``processor.decode`` returns an iterable of messages, each carrying an
        ``audio_codes_list`` of waveform tensors. The single-speaker narration
        path produces one message with one segment.
        """
        if not decoded:
            return None
        first = decoded[0]
        segments = getattr(first, "audio_codes_list", None)
        if not segments:
            return None
        return segments[0]

    def _coerce_waveform(self, audio: Any) -> np.ndarray:
        """Coerce a model audio output to a 1-D float32 numpy array.

        Returns a short silence when the model produced nothing.
        """
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
    def _as_single_speaker(text: str) -> str:
        """Wrap *text* as a single ``[S1]`` speaker turn unless already tagged."""
        if _SPEAKER_TAG_RE.match(text):
            return text
        return f"{_SINGLE_SPEAKER_TAG} {text.strip()}"

    @staticmethod
    def _read_sample_rate(processor: Any) -> int:
        """Read the output sample rate from the processor, with a safe default."""
        model_config = getattr(processor, "model_config", None)
        sampling_rate = getattr(model_config, "sampling_rate", None)
        try:
            if sampling_rate is not None:
                return int(sampling_rate)
        except (TypeError, ValueError):
            pass
        return _SAMPLE_RATE_DEFAULT

    @staticmethod
    def _resolve_language(value: str | None) -> str:
        """Validate *value* and resolve it to an ISO 639-1 code.

        MOSS-TTSD auto-detects the spoken language from the text, so there is no
        model-specific language identifier to translate to (unlike Kokoro or
        Qwen3-TTS).  This method exists to honour the application's
        ISO-639-1-in convention and to fail clearly on a malformed value.
        ``None`` or an empty string falls back to the Italian default
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
            f"Unsupported language {value!r} for MOSS-TTSD. The model "
            f"auto-detects the language from the text; pass an ISO 639-1 code "
            f"(e.g. 'it', 'en') or 'auto'."
        )

    @staticmethod
    def _detect_attn_implementation() -> str:
        """Return ``"flash_attention_2"`` if flash-attn is installed, else ``"sdpa"``.

        ``sdpa`` (PyTorch scaled-dot-product attention) is the documented
        fallback and needs no extra package, unlike FlashAttention 2.
        """
        try:
            import flash_attn  # noqa: F401

            return "flash_attention_2"
        except ImportError:
            logger.info(
                "flash-attn not installed; using sdpa attention for MOSS-TTSD. "
                "Install flash-attn for reduced GPU memory usage."
            )
            return "sdpa"
