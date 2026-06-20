"""Tests for the MOSS-TTSD v1.0 model adapter.

Covers: protocol compliance, Italian default (DEC-default-italian-language),
load/unload lifecycle via mocked transformers ``AutoModel``/``AutoProcessor``,
single-``[S1]``-speaker wrapping of narration text, the optional reference-audio
voice-cloning path, synthesize output coercion, the advisory auto-detected
language handling (no language tag is forwarded — like VoxCPM2), registry
integration, and the 24 kHz output pipeline.  All transformers / model
dependencies are mocked, so the ~19 GB model need not be installed.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
import pytest
import torch

from local_tts.tts.adapters import ModelAdapter
from local_tts.tts.adapters.moss_ttsd import (
    MOSSTTSDAdapter,
    _AUDIO_TOKENIZER_ID,
    _DEFAULT_LANGUAGE,
    _SAMPLE_RATE_DEFAULT,
    _install_transformers_compat,
)

_MODEL_ID = "OpenMOSS-Team/MOSS-TTSD-v1.0"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_mock_processor(audio_samples: int = 4800, sample_rate: int = 24000) -> MagicMock:
    """Create a mock processor mirroring the published MOSS-TTSD interface."""
    processor = MagicMock()
    processor.model_config.sampling_rate = sample_rate
    processor.build_user_message.return_value = {"role": "user"}
    processor.build_assistant_message.return_value = {"role": "assistant"}
    processor.encode_audios_from_wav.return_value = ["ref_codes"]

    batch = MagicMock()
    batch.__contains__.side_effect = lambda k: k in ("input_ids", "attention_mask")
    batch.__getitem__.side_effect = lambda k: torch.zeros(1, 4, dtype=torch.long)
    batch.to.return_value = batch
    processor.return_value = batch  # processor(conversations, mode=...) -> batch

    message = MagicMock()
    message.audio_codes_list = [torch.randn(audio_samples)]
    processor.decode.return_value = [message]

    return processor


def _loaded_adapter(
    audio_samples: int = 4800,
) -> tuple[MOSSTTSDAdapter, MagicMock, MagicMock]:
    """Create an adapter with a mocked processor + model ready for synthesis."""
    adapter = MOSSTTSDAdapter()
    processor = _make_mock_processor(audio_samples)
    model = MagicMock()
    model.generate.return_value = MagicMock()
    adapter._processor = processor
    adapter._model = model
    adapter._device = "cuda"
    adapter._sample_rate = 24000
    return adapter, processor, model


# ---------------------------------------------------------------------------
# Protocol compliance
# ---------------------------------------------------------------------------

class TestMOSSTTSDAdapterProtocol:
    def test_satisfies_model_adapter_protocol(self):
        adapter = MOSSTTSDAdapter()
        assert isinstance(adapter, ModelAdapter)

    def test_sample_rate_default_is_24000(self):
        adapter = MOSSTTSDAdapter()
        assert adapter.sample_rate == 24000
        assert adapter.sample_rate == _SAMPLE_RATE_DEFAULT


# ---------------------------------------------------------------------------
# Default configuration (DEC-default-italian-language)
# ---------------------------------------------------------------------------

class TestMOSSTTSDDefaults:
    def test_default_language_is_italian(self):
        assert _DEFAULT_LANGUAGE == "it"

    def test_resolve_language_defaults_to_italian(self):
        assert MOSSTTSDAdapter._resolve_language(None) == "it"
        assert MOSSTTSDAdapter._resolve_language("") == "it"
        assert MOSSTTSDAdapter._resolve_language("   ") == "it"


# ---------------------------------------------------------------------------
# Load / unload lifecycle
# ---------------------------------------------------------------------------

class TestMOSSTTSDAdapterLoad:
    def test_load_creates_processor_and_model(self):
        # Patch the ``from_pretrained`` methods (not the lazy-imported classes)
        # so the real call is intercepted without downloading remote code.
        mock_processor = MagicMock()
        mock_processor.audio_tokenizer = MagicMock()
        mock_processor.audio_tokenizer.to.return_value = mock_processor.audio_tokenizer
        mock_processor.model_config.sampling_rate = 24000

        mock_model_obj = MagicMock()

        with patch(
            "transformers.AutoProcessor.from_pretrained", return_value=mock_processor
        ) as mock_proc_fp, patch(
            "transformers.AutoModel.from_pretrained"
        ) as mock_model_fp:
            mock_model_fp.return_value.to.return_value = mock_model_obj
            adapter = MOSSTTSDAdapter()
            adapter.load(_MODEL_ID, "cuda")

        mock_proc_fp.assert_called_once_with(
            _MODEL_ID,
            trust_remote_code=True,
            codec_path=_AUDIO_TOKENIZER_ID,
        )
        model_call = mock_model_fp.call_args
        assert model_call.args[0] == _MODEL_ID
        assert model_call.kwargs["trust_remote_code"] is True
        assert model_call.kwargs["torch_dtype"] == torch.bfloat16
        assert model_call.kwargs["attn_implementation"] in ("sdpa", "flash_attention_2")

        # Codec moved onto the model device; model put in eval mode.
        mock_processor.audio_tokenizer.to.assert_called_once_with("cuda")
        mock_model_obj.eval.assert_called_once()

        assert adapter._processor is mock_processor
        assert adapter._model is mock_model_obj
        assert adapter._device == "cuda"
        assert adapter._sample_rate == 24000

    def test_load_does_not_pin_revision(self):
        """Regression guard: ``revision`` must NOT be passed. The processor
        forwards extra kwargs into the companion codec's ``AutoModel.from_pretrained``,
        and the codec is a different repo with different commit hashes — pinning
        ``revision`` 404s the codec load."""
        mock_processor = MagicMock()
        mock_processor.audio_tokenizer = MagicMock()
        mock_processor.model_config.sampling_rate = 24000

        with patch(
            "transformers.AutoProcessor.from_pretrained", return_value=mock_processor
        ) as mock_proc_fp, patch(
            "transformers.AutoModel.from_pretrained"
        ) as mock_model_fp:
            MOSSTTSDAdapter().load(_MODEL_ID, "cuda")

        assert "revision" not in mock_proc_fp.call_args.kwargs
        assert "revision" not in mock_model_fp.call_args.kwargs

    def test_unload_clears_state(self):
        adapter, _, _ = _loaded_adapter()
        adapter.unload()

        assert adapter._model is None
        assert adapter._processor is None
        assert adapter._device is None

    def test_unload_when_not_loaded_is_safe(self):
        adapter = MOSSTTSDAdapter()
        adapter.unload()  # Should not raise


# ---------------------------------------------------------------------------
# transformers 5.x PretrainedConfig -> PreTrainedConfig compat bridge
# ---------------------------------------------------------------------------

class TestMOSSTTSDTransformersCompat:
    """The companion audio tokenizer's remote code imports the transformers 5.x
    name ``PreTrainedConfig``; on transformers 4.x the adapter aliases it onto
    the existing ``PretrainedConfig`` class so the codec ``trust_remote_code``
    import succeeds (the bug behind 'cannot import name PreTrainedConfig')."""

    def test_install_makes_pretrainedconfig_importable(self):
        _install_transformers_compat()
        from transformers.configuration_utils import (  # noqa: F401
            PretrainedConfig,
            PreTrainedConfig,
        )

        # In 5.x they are the same (deprecated alias); in 4.x we alias them.
        assert PreTrainedConfig is PretrainedConfig

    def test_install_is_idempotent(self):
        _install_transformers_compat()
        _install_transformers_compat()  # second call must not raise
        from transformers.configuration_utils import PreTrainedConfig

        assert PreTrainedConfig is not None

    def test_install_does_not_overwrite_existing(self):
        from transformers import configuration_utils as cu

        had = hasattr(cu, "PreTrainedConfig")
        saved = getattr(cu, "PreTrainedConfig", None)
        sentinel = object()
        cu.PreTrainedConfig = sentinel
        try:
            _install_transformers_compat()
            assert cu.PreTrainedConfig is sentinel
        finally:
            if had:
                cu.PreTrainedConfig = saved
            else:
                cu.PreTrainedConfig = cu.PretrainedConfig


# ---------------------------------------------------------------------------
# Synthesize — single-speaker narration
# ---------------------------------------------------------------------------

class TestMOSSTTSDAdapterSynthesize:
    def test_returns_float32_numpy_array(self):
        adapter, _, _ = _loaded_adapter()
        audio = adapter.synthesize("Ciao mondo")
        assert isinstance(audio, np.ndarray)
        assert audio.dtype == np.float32
        assert len(audio) > 0

    def test_returns_correct_audio_length(self):
        adapter, _, _ = _loaded_adapter(audio_samples=9600)
        audio = adapter.synthesize("Ciao mondo")
        assert len(audio) == 9600

    def test_plain_text_wrapped_as_single_speaker_turn(self):
        adapter, processor, _ = _loaded_adapter()
        adapter.synthesize("Ciao mondo")
        kwargs = processor.build_user_message.call_args.kwargs
        assert kwargs["text"] == "[S1] Ciao mondo"
        assert kwargs["reference"] is None

    def test_existing_speaker_tag_not_double_wrapped(self):
        adapter, processor, _ = _loaded_adapter()
        adapter.synthesize("[S1] Già marcato")
        kwargs = processor.build_user_message.call_args.kwargs
        assert kwargs["text"] == "[S1] Già marcato"

    def test_uses_generation_mode_single_user_message(self):
        """Single-voice narration must use generation mode (a lone user
        message). continuation mode requires a trailing assistant turn and would
        raise an (empty) ValueError in the processor."""
        adapter, processor, _ = _loaded_adapter()
        adapter.synthesize("Ciao mondo")
        # The processor was called as processor([conversation], mode="generation").
        assert processor.call_args.kwargs.get("mode") == "generation"
        conversation = processor.call_args.args[0][0]
        assert len(conversation) == 1  # a single (user) message
        # No assistant message is built (that is continuation-mode only).
        processor.build_assistant_message.assert_not_called()

    def test_no_reference_passes_none_reference(self):
        adapter, processor, _ = _loaded_adapter()
        adapter.synthesize("Ciao mondo")
        assert processor.build_user_message.call_args.kwargs["reference"] is None

    def test_reference_audio_attached_to_user_message(self):
        """An optional reference clip path is attached to the user message's
        ``reference``; the processor encodes it itself (no encode_audios_from_wav
        call from the adapter)."""
        adapter, processor, _ = _loaded_adapter()
        adapter.synthesize("Ciao", voice="/path/to/ref.wav")

        user_kwargs = processor.build_user_message.call_args.kwargs
        assert user_kwargs["reference"] == ["/path/to/ref.wav"]
        assert user_kwargs["text"] == "[S1] Ciao"
        processor.build_assistant_message.assert_not_called()

    def test_generate_called_with_default_max_new_tokens(self):
        adapter, _, model = _loaded_adapter()
        adapter.synthesize("Ciao")
        assert model.generate.call_args.kwargs["max_new_tokens"] == 2000

    def test_generate_max_new_tokens_overridable(self):
        adapter, _, model = _loaded_adapter()
        adapter.synthesize("Ciao", max_new_tokens=512)
        assert model.generate.call_args.kwargs["max_new_tokens"] == 512

    def test_generate_receives_batch_tensors(self):
        adapter, _, model = _loaded_adapter()
        adapter.synthesize("Ciao")
        gen_kwargs = model.generate.call_args.kwargs
        assert "input_ids" in gen_kwargs
        assert "attention_mask" in gen_kwargs

    def test_torch_tensor_converted_to_numpy(self):
        adapter, processor, _ = _loaded_adapter()
        message = MagicMock()
        message.audio_codes_list = [torch.randn(2000)]
        processor.decode.return_value = [message]
        audio = adapter.synthesize("Test")
        assert isinstance(audio, np.ndarray)
        assert audio.dtype == np.float32
        assert len(audio) == 2000

    def test_multidim_output_flattened(self):
        adapter, processor, _ = _loaded_adapter()
        message = MagicMock()
        message.audio_codes_list = [np.random.randn(1, 1500).astype(np.float32)]
        processor.decode.return_value = [message]
        audio = adapter.synthesize("Test")
        assert audio.ndim == 1
        assert len(audio) == 1500

    def test_empty_decode_returns_silence(self):
        adapter, processor, _ = _loaded_adapter()
        processor.decode.return_value = []
        audio = adapter.synthesize("...")
        assert isinstance(audio, np.ndarray)
        assert audio.dtype == np.float32
        assert len(audio) == int(_SAMPLE_RATE_DEFAULT * 0.1)
        assert np.all(audio == 0.0)

    def test_empty_audio_segment_returns_silence(self):
        adapter, processor, _ = _loaded_adapter()
        message = MagicMock()
        message.audio_codes_list = [np.array([], dtype=np.float32)]
        processor.decode.return_value = [message]
        audio = adapter.synthesize("...")
        assert len(audio) == int(_SAMPLE_RATE_DEFAULT * 0.1)

    def test_missing_audio_codes_returns_silence(self):
        adapter, processor, _ = _loaded_adapter()
        message = MagicMock()
        message.audio_codes_list = []
        processor.decode.return_value = [message]
        audio = adapter.synthesize("...")
        assert len(audio) == int(_SAMPLE_RATE_DEFAULT * 0.1)

    def test_synthesize_without_load_raises(self):
        adapter = MOSSTTSDAdapter()
        with pytest.raises(RuntimeError, match="load.*must be called"):
            adapter.synthesize("Ciao")


# ---------------------------------------------------------------------------
# Language handling (advisory: MOSS-TTSD auto-detects; kwarg is validated only)
# ---------------------------------------------------------------------------

class TestMOSSTTSDLanguageHandling:
    """MOSS-TTSD auto-detects the language from the text, so the ISO 639-1
    ``language`` kwarg forwarded by the application layer is validated and
    defaulted to Italian but is NOT passed to the model."""

    def test_iso_code_it_accepted_and_not_forwarded(self):
        adapter, processor, model = _loaded_adapter()
        adapter.synthesize("Ciao", language="it")
        # Auto-detection: no language identifier reaches the model or processor.
        assert "language" not in model.generate.call_args.kwargs
        assert "language" not in processor.build_user_message.call_args.kwargs

    def test_iso_code_en_accepted(self):
        adapter, _, model = _loaded_adapter()
        adapter.synthesize("Hello", language="en")  # Should not raise
        assert model.generate.called

    def test_iso_code_is_case_insensitive(self):
        assert MOSSTTSDAdapter._resolve_language("IT") == "it"

    def test_auto_is_accepted(self):
        assert MOSSTTSDAdapter._resolve_language("auto") == "auto"

    def test_unsupported_language_raises(self):
        adapter, _, _ = _loaded_adapter()
        with pytest.raises(ValueError, match="Unsupported language"):
            adapter.synthesize("Hello", language="english")

    def test_malformed_language_raises(self):
        with pytest.raises(ValueError, match="Unsupported language"):
            MOSSTTSDAdapter._resolve_language("123")


# ---------------------------------------------------------------------------
# 24 kHz output pipeline
# ---------------------------------------------------------------------------

class TestMOSSTTSD24kHzPipeline:
    def test_encode_to_mp3_handles_24khz(self, tmp_path: Path):
        """The synthesizer reads the rate from the adapter and pydub/ffmpeg
        encode it, so the 24 kHz output needs no special handling."""
        from local_tts.tts.synthesizer import encode_to_mp3

        adapter, _, _ = _loaded_adapter()
        waveform = np.random.randn(adapter.sample_rate).astype(np.float32) * 0.1
        out = tmp_path / "chapter-01.mp3"
        duration = encode_to_mp3(waveform, adapter.sample_rate, out)

        assert out.exists()
        assert out.stat().st_size > 0
        assert duration == pytest.approx(1.0, abs=0.1)


# ---------------------------------------------------------------------------
# Registry integration
# ---------------------------------------------------------------------------

class TestMOSSTTSDAdapterRegistry:
    def test_moss_ttsd_registered_in_adapter_registry(self):
        from local_tts.tts.adapters import get_adapter, has_adapter

        assert has_adapter(_MODEL_ID) is True
        adapter = get_adapter(_MODEL_ID)
        assert adapter is not None
        assert isinstance(adapter, MOSSTTSDAdapter)
        assert isinstance(adapter, ModelAdapter)

    def test_moss_ttsd_in_compatible_models_as_foss(self):
        from local_tts.tts.model_loader import COMPATIBLE_MODELS

        entry = COMPATIBLE_MODELS[_MODEL_ID]
        assert entry.license == "Apache-2.0"
        assert entry.license_is_foss is True
        assert entry.license_notice is None

    def test_moss_ttsd_loader_available_via_list_models(self):
        from local_tts.tts.model_loader import ModelLoader

        with patch("local_tts.tts.model_loader.scan_cache_dir") as mock_scan:
            mock_scan.return_value = MagicMock(repos=[])
            by_id = {m.model_id: m for m in ModelLoader().list_models()}
        assert by_id[_MODEL_ID].loader_available is True
