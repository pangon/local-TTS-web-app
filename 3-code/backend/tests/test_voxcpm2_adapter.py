"""Tests for the VoxCPM2 model adapter.

Covers: protocol compliance, Italian default (DEC-default-italian-language),
load/unload lifecycle, synthesize output format, voice (reference-audio) and
generation kwargs, the advisory auto-detected language handling, the
confirmed-text guarantee (no built-in re-normalization), registry
integration, and the 48 kHz output pipeline.  All ``voxcpm`` package
dependencies are mocked, so the real package need not be installed.
"""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
import pytest
import torch

from local_tts.tts.adapters import ModelAdapter
from local_tts.tts.adapters.voxcpm2 import (
    VoxCPM2Adapter,
    _DEFAULT_LANGUAGE,
    _SAMPLE_RATE,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_mock_model(audio_samples: int = 4800) -> MagicMock:
    """Create a mock VoxCPM model whose generate() returns audio samples."""
    model = MagicMock()
    model.generate.return_value = np.random.randn(audio_samples).astype(np.float32)
    return model


def _loaded_adapter(audio_samples: int = 4800) -> tuple[VoxCPM2Adapter, MagicMock]:
    """Create an adapter with a mocked model ready for synthesis."""
    adapter = VoxCPM2Adapter()
    mock_model = _make_mock_model(audio_samples)
    adapter._model = mock_model
    adapter._device = "cuda"
    return adapter, mock_model


# ---------------------------------------------------------------------------
# Protocol compliance
# ---------------------------------------------------------------------------

class TestVoxCPM2AdapterProtocol:
    def test_satisfies_model_adapter_protocol(self):
        adapter = VoxCPM2Adapter()
        assert isinstance(adapter, ModelAdapter)

    def test_sample_rate_is_48000(self):
        adapter = VoxCPM2Adapter()
        assert adapter.sample_rate == 48000
        assert adapter.sample_rate == _SAMPLE_RATE


# ---------------------------------------------------------------------------
# Default configuration (DEC-default-italian-language)
# ---------------------------------------------------------------------------

class TestVoxCPM2Defaults:
    def test_default_language_is_italian(self):
        assert _DEFAULT_LANGUAGE == "it"

    def test_resolve_language_defaults_to_italian(self):
        assert VoxCPM2Adapter._resolve_language(None) == "it"
        assert VoxCPM2Adapter._resolve_language("") == "it"
        assert VoxCPM2Adapter._resolve_language("   ") == "it"

    def test_synthesize_uses_builtin_voice_by_default(self):
        """No reference audio → built-in voice (Italian phonemes for Italian text)."""
        adapter, mock_model = _loaded_adapter()
        adapter.synthesize("Ciao mondo")
        mock_model.generate.assert_called_once_with(
            text="Ciao mondo",
            prompt_wav_path=None,
            prompt_text=None,
            normalize=False,
        )


# ---------------------------------------------------------------------------
# Load / unload lifecycle
# ---------------------------------------------------------------------------

class TestVoxCPM2AdapterLoad:
    def test_load_creates_model(self):
        mock_voxcpm_cls = MagicMock()
        mock_instance = MagicMock()
        mock_voxcpm_cls.from_pretrained.return_value = mock_instance

        fake_voxcpm = MagicMock()
        fake_voxcpm.VoxCPM = mock_voxcpm_cls

        with patch.dict(sys.modules, {"voxcpm": fake_voxcpm}):
            adapter = VoxCPM2Adapter()
            adapter.load("openbmb/VoxCPM2", "cuda")

        mock_voxcpm_cls.from_pretrained.assert_called_once_with("openbmb/VoxCPM2")
        assert adapter._model is mock_instance
        assert adapter._device == "cuda"

    def test_unload_clears_state(self):
        adapter, _ = _loaded_adapter()
        adapter.unload()

        assert adapter._model is None
        assert adapter._device is None

    def test_unload_when_not_loaded_is_safe(self):
        adapter = VoxCPM2Adapter()
        adapter.unload()  # Should not raise


# ---------------------------------------------------------------------------
# Synthesize
# ---------------------------------------------------------------------------

class TestVoxCPM2AdapterSynthesize:
    def test_returns_float32_numpy_array(self):
        adapter, _ = _loaded_adapter()
        audio = adapter.synthesize("Hello world")
        assert isinstance(audio, np.ndarray)
        assert audio.dtype == np.float32
        assert len(audio) > 0

    def test_returns_correct_audio_length(self):
        adapter, _ = _loaded_adapter(audio_samples=9600)
        audio = adapter.synthesize("Hello world")
        assert len(audio) == 9600

    def test_reference_audio_voice_passed_as_prompt(self):
        adapter, mock_model = _loaded_adapter()
        adapter.synthesize("Ciao", voice="/path/to/ref.wav", prompt_text="Riferimento")
        mock_model.generate.assert_called_once_with(
            text="Ciao",
            prompt_wav_path="/path/to/ref.wav",
            prompt_text="Riferimento",
            normalize=False,
        )

    def test_does_not_renormalize_confirmed_text_by_default(self):
        """The app feeds exact user-confirmed text; VoxCPM's normalizer is off
        by default so the confirmed-text guarantee holds (DEC-preprocess-review-flow)."""
        adapter, mock_model = _loaded_adapter()
        adapter.synthesize("1.234,56")
        assert mock_model.generate.call_args.kwargs["normalize"] is False

    def test_normalize_can_be_overridden(self):
        adapter, mock_model = _loaded_adapter()
        adapter.synthesize("Test", normalize=True)
        assert mock_model.generate.call_args.kwargs["normalize"] is True

    def test_generation_kwargs_passed_through_when_provided(self):
        adapter, mock_model = _loaded_adapter()
        adapter.synthesize("Test", cfg_value=2.5, inference_timesteps=20)
        kwargs = mock_model.generate.call_args.kwargs
        assert kwargs["cfg_value"] == 2.5
        assert kwargs["inference_timesteps"] == 20

    def test_generation_kwargs_omitted_when_not_provided(self):
        adapter, mock_model = _loaded_adapter()
        adapter.synthesize("Test")
        kwargs = mock_model.generate.call_args.kwargs
        assert "cfg_value" not in kwargs
        assert "inference_timesteps" not in kwargs

    def test_none_output_returns_silence(self):
        adapter, mock_model = _loaded_adapter()
        mock_model.generate.return_value = None
        audio = adapter.synthesize("...")
        assert isinstance(audio, np.ndarray)
        assert audio.dtype == np.float32
        assert len(audio) == int(_SAMPLE_RATE * 0.1)
        assert np.all(audio == 0.0)

    def test_empty_output_returns_silence(self):
        adapter, mock_model = _loaded_adapter()
        mock_model.generate.return_value = np.array([], dtype=np.float32)
        audio = adapter.synthesize("...")
        assert isinstance(audio, np.ndarray)
        assert len(audio) == int(_SAMPLE_RATE * 0.1)

    def test_torch_tensor_converted_to_numpy(self):
        adapter, mock_model = _loaded_adapter()
        mock_model.generate.return_value = torch.randn(2000)
        audio = adapter.synthesize("Test")
        assert isinstance(audio, np.ndarray)
        assert audio.dtype == np.float32
        assert len(audio) == 2000

    def test_multidim_output_flattened(self):
        adapter, mock_model = _loaded_adapter()
        mock_model.generate.return_value = np.random.randn(1, 1500).astype(np.float32)
        audio = adapter.synthesize("Test")
        assert audio.ndim == 1
        assert len(audio) == 1500

    def test_synthesize_without_load_raises(self):
        adapter = VoxCPM2Adapter()
        with pytest.raises(RuntimeError, match="load.*must be called"):
            adapter.synthesize("Hello")


# ---------------------------------------------------------------------------
# Language handling (advisory: VoxCPM2 auto-detects; kwarg is validated only)
# ---------------------------------------------------------------------------

class TestVoxCPM2LanguageHandling:
    """VoxCPM2 auto-detects the language from the text, so the ISO 639-1
    ``language`` kwarg forwarded by the application layer is validated and
    defaulted to Italian but is NOT passed to the model."""

    def test_iso_code_it_accepted_and_not_forwarded(self):
        adapter, mock_model = _loaded_adapter()
        adapter.synthesize("Ciao", language="it")
        # Auto-detection: no language identifier reaches the model.
        kwargs = mock_model.generate.call_args.kwargs
        assert "language" not in kwargs

    def test_iso_code_en_accepted(self):
        adapter, mock_model = _loaded_adapter()
        adapter.synthesize("Hello", language="en")  # Should not raise
        assert mock_model.generate.called

    def test_iso_code_is_case_insensitive(self):
        assert VoxCPM2Adapter._resolve_language("IT") == "it"

    def test_auto_is_accepted(self):
        assert VoxCPM2Adapter._resolve_language("auto") == "auto"

    def test_unsupported_language_raises(self):
        adapter, _ = _loaded_adapter()
        with pytest.raises(ValueError, match="Unsupported language"):
            adapter.synthesize("Hello", language="english")

    def test_malformed_language_raises(self):
        with pytest.raises(ValueError, match="Unsupported language"):
            VoxCPM2Adapter._resolve_language("123")


# ---------------------------------------------------------------------------
# 48 kHz output pipeline
# ---------------------------------------------------------------------------

class TestVoxCPM248kHzPipeline:
    def test_encode_to_mp3_handles_48khz(self, tmp_path: Path):
        """The synthesizer reads the rate from the adapter and pydub/ffmpeg
        encode any rate, so the 48 kHz output needs no special handling."""
        from local_tts.tts.synthesizer import encode_to_mp3

        adapter, _ = _loaded_adapter()
        waveform = np.random.randn(_SAMPLE_RATE).astype(np.float32) * 0.1
        out = tmp_path / "chapter-01.mp3"
        duration = encode_to_mp3(waveform, adapter.sample_rate, out)

        assert out.exists()
        assert out.stat().st_size > 0
        assert duration == pytest.approx(1.0, abs=0.1)


# ---------------------------------------------------------------------------
# Registry integration
# ---------------------------------------------------------------------------

class TestVoxCPM2AdapterRegistry:
    def test_voxcpm2_registered_in_adapter_registry(self):
        from local_tts.tts.adapters import get_adapter, has_adapter

        assert has_adapter("openbmb/VoxCPM2") is True
        adapter = get_adapter("openbmb/VoxCPM2")
        assert adapter is not None
        assert isinstance(adapter, VoxCPM2Adapter)
        assert isinstance(adapter, ModelAdapter)

    def test_voxcpm2_in_compatible_models_as_foss(self):
        from local_tts.tts.model_loader import COMPATIBLE_MODELS

        entry = COMPATIBLE_MODELS["openbmb/VoxCPM2"]
        assert entry.license == "Apache-2.0"
        assert entry.license_is_foss is True
        assert entry.license_notice is None

    def test_voxcpm2_loader_available_via_list_models(self):
        from unittest.mock import patch as _patch

        from local_tts.tts.model_loader import ModelLoader

        with _patch("local_tts.tts.model_loader.scan_cache_dir") as mock_scan:
            mock_scan.return_value = MagicMock(repos=[])
            by_id = {m.model_id: m for m in ModelLoader().list_models()}
        assert by_id["openbmb/VoxCPM2"].loader_available is True
