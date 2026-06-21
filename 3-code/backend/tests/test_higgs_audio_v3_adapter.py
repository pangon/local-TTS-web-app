"""Tests for the Higgs Audio v3 TTS model adapter.

Covers: protocol compliance, Italian default (DEC-default-italian-language),
load/unload lifecycle via a mocked transformers ``text-to-speech`` pipeline,
synthesize output coercion (dict / list-of-dict / tensor / multidim / empty),
``generate_kwargs`` token cap, the optional reference-audio voice-cloning path,
the advisory auto-detected language handling (no language tag is forwarded —
like VoxCPM2 / MOSS-TTSD / Fish S2-Pro), the non-FOSS license metadata
(DEC-model-license-disclosure), registry integration, and the 24 kHz output
pipeline.  The transformers pipeline is mocked, so the ~9.3 GB model need not be
installed and transformers >= 5.5 is not required to run these tests.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
import pytest
import torch

from local_tts.tts.adapters import ModelAdapter
from local_tts.tts.adapters.higgs_audio_v3 import (
    HiggsAudioV3Adapter,
    _DEFAULT_LANGUAGE,
    _DEFAULT_MAX_NEW_TOKENS,
    _SAMPLE_RATE_DEFAULT,
    _TTS_TASK,
)

_MODEL_ID = "bosonai/higgs-audio-v3-tts-4b"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_mock_pipe(audio_samples: int = 4800, sample_rate: int = 24000) -> MagicMock:
    """Create a mock TTS pipeline returning the transformers TTS contract."""
    pipe = MagicMock()
    pipe.sampling_rate = sample_rate
    pipe.return_value = {
        "audio": np.random.randn(audio_samples).astype(np.float32) * 0.1,
        "sampling_rate": sample_rate,
    }
    return pipe


def _loaded_adapter(
    audio_samples: int = 4800,
    sample_rate: int = 24000,
) -> tuple[HiggsAudioV3Adapter, MagicMock]:
    """Create an adapter with a mocked pipeline ready for synthesis."""
    adapter = HiggsAudioV3Adapter()
    pipe = _make_mock_pipe(audio_samples, sample_rate)
    adapter._pipe = pipe
    adapter._device = "cuda"
    adapter._sample_rate = sample_rate
    return adapter, pipe


# ---------------------------------------------------------------------------
# Protocol compliance
# ---------------------------------------------------------------------------

class TestHiggsAudioV3AdapterProtocol:
    def test_satisfies_model_adapter_protocol(self):
        adapter = HiggsAudioV3Adapter()
        assert isinstance(adapter, ModelAdapter)

    def test_sample_rate_default_is_24000(self):
        adapter = HiggsAudioV3Adapter()
        assert adapter.sample_rate == 24000
        assert adapter.sample_rate == _SAMPLE_RATE_DEFAULT


# ---------------------------------------------------------------------------
# Default configuration (DEC-default-italian-language)
# ---------------------------------------------------------------------------

class TestHiggsAudioV3Defaults:
    def test_default_language_is_italian(self):
        assert _DEFAULT_LANGUAGE == "it"

    def test_resolve_language_defaults_to_italian(self):
        assert HiggsAudioV3Adapter._resolve_language(None) == "it"
        assert HiggsAudioV3Adapter._resolve_language("") == "it"
        assert HiggsAudioV3Adapter._resolve_language("   ") == "it"


# ---------------------------------------------------------------------------
# Load / unload lifecycle
# ---------------------------------------------------------------------------

class TestHiggsAudioV3AdapterLoad:
    def test_load_builds_tts_pipeline(self):
        mock_pipe = _make_mock_pipe()
        with patch("local_tts.tts.adapters.higgs_audio_v3.pipeline", return_value=mock_pipe) as mock_factory:
            adapter = HiggsAudioV3Adapter()
            adapter.load(_MODEL_ID, "cuda")

        call = mock_factory.call_args
        assert call.args[0] == _TTS_TASK
        assert call.kwargs["model"] == _MODEL_ID
        assert call.kwargs["device"] == "cuda"
        assert call.kwargs["torch_dtype"] == torch.bfloat16
        assert adapter._pipe is mock_pipe
        assert adapter._device == "cuda"

    def test_load_reads_sample_rate_from_pipeline(self):
        mock_pipe = _make_mock_pipe(sample_rate=44100)
        with patch("local_tts.tts.adapters.higgs_audio_v3.pipeline", return_value=mock_pipe):
            adapter = HiggsAudioV3Adapter()
            adapter.load(_MODEL_ID, "cuda")
        assert adapter.sample_rate == 44100

    def test_load_falls_back_to_default_sample_rate(self):
        mock_pipe = MagicMock()
        mock_pipe.sampling_rate = None
        mock_pipe.model.config = MagicMock(spec=[])  # no rate attributes
        with patch("local_tts.tts.adapters.higgs_audio_v3.pipeline", return_value=mock_pipe):
            adapter = HiggsAudioV3Adapter()
            adapter.load(_MODEL_ID, "cuda")
        assert adapter.sample_rate == _SAMPLE_RATE_DEFAULT

    def test_load_does_not_use_trust_remote_code(self):
        """The architecture is native in transformers >= 5.5 — no remote code."""
        mock_pipe = _make_mock_pipe()
        with patch("local_tts.tts.adapters.higgs_audio_v3.pipeline", return_value=mock_pipe) as mock_factory:
            HiggsAudioV3Adapter().load(_MODEL_ID, "cuda")
        assert "trust_remote_code" not in mock_factory.call_args.kwargs

    def test_load_failure_raises_runtime_error_explaining_server_only(self):
        """The pipeline build fails because the architecture is absent from
        transformers; the wrapped RuntimeError explains the real cause (server-only,
        not transformers-native) and points at DEC-single-process."""
        with patch(
            "local_tts.tts.adapters.higgs_audio_v3.pipeline",
            side_effect=KeyError("higgs_multimodal_qwen3"),
        ):
            adapter = HiggsAudioV3Adapter()
            with pytest.raises(RuntimeError, match="not implemented in the transformers"):
                adapter.load(_MODEL_ID, "cuda")

    def test_unload_clears_state(self):
        adapter, _ = _loaded_adapter()
        adapter.unload()
        assert adapter._pipe is None
        assert adapter._device is None

    def test_unload_when_not_loaded_is_safe(self):
        adapter = HiggsAudioV3Adapter()
        adapter.unload()  # Should not raise


# ---------------------------------------------------------------------------
# Synthesize
# ---------------------------------------------------------------------------

class TestHiggsAudioV3AdapterSynthesize:
    def test_returns_float32_numpy_array(self):
        adapter, _ = _loaded_adapter()
        audio = adapter.synthesize("Ciao mondo")
        assert isinstance(audio, np.ndarray)
        assert audio.dtype == np.float32
        assert len(audio) > 0

    def test_returns_correct_audio_length(self):
        adapter, _ = _loaded_adapter(audio_samples=9600)
        audio = adapter.synthesize("Ciao mondo")
        assert len(audio) == 9600

    def test_text_passed_to_pipeline(self):
        adapter, pipe = _loaded_adapter()
        adapter.synthesize("Ciao mondo")
        assert pipe.call_args.args[0] == "Ciao mondo"

    def test_generate_kwargs_default_max_new_tokens(self):
        adapter, pipe = _loaded_adapter()
        adapter.synthesize("Ciao")
        gen = pipe.call_args.kwargs["generate_kwargs"]
        assert gen["max_new_tokens"] == _DEFAULT_MAX_NEW_TOKENS

    def test_generate_kwargs_max_new_tokens_overridable(self):
        adapter, pipe = _loaded_adapter()
        adapter.synthesize("Ciao", max_new_tokens=512)
        assert pipe.call_args.kwargs["generate_kwargs"]["max_new_tokens"] == 512

    def test_no_voice_passes_no_reference(self):
        adapter, pipe = _loaded_adapter()
        adapter.synthesize("Ciao")
        assert "forward_params" not in pipe.call_args.kwargs

    def test_reference_audio_attached_via_forward_params(self):
        adapter, pipe = _loaded_adapter()
        adapter.synthesize("Ciao", voice="/path/to/ref.wav", prompt_text="riferimento")
        forward = pipe.call_args.kwargs["forward_params"]
        assert forward["reference_audio"] == "/path/to/ref.wav"
        assert forward["reference_text"] == "riferimento"

    def test_reference_audio_without_prompt_text_defaults_empty(self):
        adapter, pipe = _loaded_adapter()
        adapter.synthesize("Ciao", voice="/path/to/ref.wav")
        assert pipe.call_args.kwargs["forward_params"]["reference_text"] == ""

    def test_dict_output_coerced(self):
        adapter, pipe = _loaded_adapter()
        pipe.return_value = {"audio": np.random.randn(2000).astype(np.float32),
                             "sampling_rate": 24000}
        audio = adapter.synthesize("Test")
        assert audio.dtype == np.float32
        assert len(audio) == 2000

    def test_list_of_dict_output_coerced(self):
        adapter, pipe = _loaded_adapter()
        pipe.return_value = [{"audio": np.random.randn(1800).astype(np.float32),
                              "sampling_rate": 24000}]
        audio = adapter.synthesize("Test")
        assert len(audio) == 1800

    def test_tensor_output_converted_to_numpy(self):
        adapter, pipe = _loaded_adapter()
        pipe.return_value = {"audio": torch.randn(1500), "sampling_rate": 24000}
        audio = adapter.synthesize("Test")
        assert isinstance(audio, np.ndarray)
        assert audio.dtype == np.float32
        assert len(audio) == 1500

    def test_multidim_output_flattened(self):
        adapter, pipe = _loaded_adapter()
        pipe.return_value = {"audio": np.random.randn(1, 1200).astype(np.float32),
                             "sampling_rate": 24000}
        audio = adapter.synthesize("Test")
        assert audio.ndim == 1
        assert len(audio) == 1200

    def test_sample_rate_updated_from_output(self):
        adapter, pipe = _loaded_adapter()
        pipe.return_value = {"audio": np.random.randn(1000).astype(np.float32),
                             "sampling_rate": 48000}
        adapter.synthesize("Test")
        assert adapter.sample_rate == 48000

    def test_empty_audio_returns_silence(self):
        adapter, pipe = _loaded_adapter()
        pipe.return_value = {"audio": np.array([], dtype=np.float32),
                             "sampling_rate": 24000}
        audio = adapter.synthesize("...")
        assert len(audio) == int(_SAMPLE_RATE_DEFAULT * 0.1)
        assert np.all(audio == 0.0)

    def test_none_audio_returns_silence(self):
        adapter, pipe = _loaded_adapter()
        pipe.return_value = {"audio": None, "sampling_rate": 24000}
        audio = adapter.synthesize("...")
        assert len(audio) == int(_SAMPLE_RATE_DEFAULT * 0.1)

    def test_empty_list_output_returns_silence(self):
        adapter, pipe = _loaded_adapter()
        pipe.return_value = []
        audio = adapter.synthesize("...")
        assert len(audio) == int(_SAMPLE_RATE_DEFAULT * 0.1)

    def test_synthesize_without_load_raises(self):
        adapter = HiggsAudioV3Adapter()
        with pytest.raises(RuntimeError, match="load.*must be called"):
            adapter.synthesize("Ciao")


# ---------------------------------------------------------------------------
# Language handling (advisory: Higgs v3 auto-detects; kwarg is validated only)
# ---------------------------------------------------------------------------

class TestHiggsAudioV3LanguageHandling:
    """Higgs Audio v3 auto-detects the language from the text, so the ISO 639-1
    ``language`` kwarg forwarded by the application layer is validated and
    defaulted to Italian but is NOT passed to the model."""

    def test_iso_code_it_accepted_and_not_forwarded(self):
        adapter, pipe = _loaded_adapter()
        adapter.synthesize("Ciao", language="it")
        # Auto-detection: no language identifier reaches the pipeline.
        assert "language" not in pipe.call_args.kwargs
        assert pipe.call_args.kwargs.get("forward_params", {}).get("language") is None

    def test_iso_code_en_accepted(self):
        adapter, pipe = _loaded_adapter()
        adapter.synthesize("Hello", language="en")  # Should not raise
        assert pipe.called

    def test_iso_code_is_case_insensitive(self):
        assert HiggsAudioV3Adapter._resolve_language("IT") == "it"

    def test_auto_is_accepted(self):
        assert HiggsAudioV3Adapter._resolve_language("auto") == "auto"

    def test_unsupported_language_raises(self):
        adapter, _ = _loaded_adapter()
        with pytest.raises(ValueError, match="Unsupported language"):
            adapter.synthesize("Hello", language="english")

    def test_malformed_language_raises(self):
        with pytest.raises(ValueError, match="Unsupported language"):
            HiggsAudioV3Adapter._resolve_language("123")


# ---------------------------------------------------------------------------
# 24 kHz output pipeline
# ---------------------------------------------------------------------------

class TestHiggsAudioV324kHzPipeline:
    def test_encode_to_mp3_handles_24khz(self, tmp_path: Path):
        """The synthesizer reads the rate from the adapter and pydub/ffmpeg
        encode it, so the 24 kHz output needs no special handling."""
        from local_tts.tts.synthesizer import encode_to_mp3

        adapter, _ = _loaded_adapter()
        waveform = np.random.randn(adapter.sample_rate).astype(np.float32) * 0.1
        out = tmp_path / "chapter-01.mp3"
        duration = encode_to_mp3(waveform, adapter.sample_rate, out)

        assert out.exists()
        assert out.stat().st_size > 0
        assert duration == pytest.approx(1.0, abs=0.1)


# ---------------------------------------------------------------------------
# Registry integration & license metadata
# ---------------------------------------------------------------------------

class TestHiggsAudioV3AdapterRegistry:
    def test_higgs_v3_intentionally_not_registered(self):
        """Higgs v3 is published server-only (vLLM-Omni/SGLang-Omni); its
        architecture is not in transformers and the repo ships no remote code,
        so it cannot load in-process (DEC-single-process). The adapter is
        deliberately UNREGISTERED (module retained for future native support)."""
        from local_tts.tts.adapters import get_adapter, has_adapter

        assert has_adapter(_MODEL_ID) is False
        assert get_adapter(_MODEL_ID) is None

    def test_higgs_v3_in_compatible_models_as_non_foss_with_notice(self):
        # Still LISTED in the catalog (with its license disclosure) even though
        # it has no adapter — like Qwen3-TTS / CosyVoice / XTTS.
        from local_tts.tts.model_loader import COMPATIBLE_MODELS

        entry = COMPATIBLE_MODELS[_MODEL_ID]
        assert "Boson" in entry.license
        assert entry.license_is_foss is False
        assert entry.license_notice  # non-empty disclosure (DEC-model-license-disclosure)
        assert "commercial" in entry.license_notice.lower()

    def test_higgs_v3_not_loader_available_but_still_non_foss_via_list_models(self):
        from local_tts.tts.model_loader import ModelLoader

        with patch("local_tts.tts.model_loader.scan_cache_dir") as mock_scan:
            mock_scan.return_value = MagicMock(repos=[])
            by_id = {m.model_id: m for m in ModelLoader().list_models()}
        model = by_id[_MODEL_ID]
        assert model.loader_available is False  # no adapter -> UI hides download/load
        assert model.license_is_foss is False
        assert model.license_notice
