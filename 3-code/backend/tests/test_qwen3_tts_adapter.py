"""Tests for the Qwen3-TTS model adapter.

Covers: protocol compliance, load/unload lifecycle, synthesize output
format, speaker and language kwargs handling, instruct parameter,
FlashAttention detection, and error handling.
All qwen_tts package dependencies are mocked.
"""

from __future__ import annotations

import sys
from typing import Any
from unittest.mock import MagicMock, patch

import numpy as np
import pytest
import torch

from local_tts.tts.adapters import ModelAdapter
from local_tts.tts.adapters.qwen3_tts import (
    Qwen3TTSAdapter,
    SUPPORTED_LANGUAGES,
    SUPPORTED_SPEAKERS,
    _DEFAULT_LANGUAGE,
    _DEFAULT_SPEAKER,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_mock_model(
    audio_samples: int = 2400,
    sample_rate: int = 24000,
) -> MagicMock:
    """Create a mock Qwen3TTSModel that returns audio from generate_custom_voice."""
    model = MagicMock()
    wav = np.random.randn(audio_samples).astype(np.float32)
    model.generate_custom_voice.return_value = ([wav], sample_rate)
    return model


def _loaded_adapter(
    audio_samples: int = 2400,
    sample_rate: int = 24000,
) -> tuple[Qwen3TTSAdapter, MagicMock]:
    """Create an adapter with a mocked model ready for synthesis."""
    adapter = Qwen3TTSAdapter()
    mock_model = _make_mock_model(audio_samples, sample_rate)
    adapter._model = mock_model
    adapter._device = "cuda"
    adapter._sample_rate = sample_rate
    return adapter, mock_model


# ---------------------------------------------------------------------------
# Protocol compliance
# ---------------------------------------------------------------------------

class TestQwen3TTSAdapterProtocol:
    def test_satisfies_model_adapter_protocol(self):
        adapter = Qwen3TTSAdapter()
        assert isinstance(adapter, ModelAdapter)

    def test_default_sample_rate_is_24000(self):
        adapter = Qwen3TTSAdapter()
        assert adapter.sample_rate == 24000


# ---------------------------------------------------------------------------
# Default configuration (DEC-default-italian-language)
# ---------------------------------------------------------------------------

class TestQwen3TTSDefaults:
    def test_default_language_is_italian(self):
        assert _DEFAULT_LANGUAGE == "Italian"

    def test_default_speaker_is_set(self):
        assert _DEFAULT_SPEAKER in SUPPORTED_SPEAKERS

    def test_italian_in_supported_languages(self):
        assert "Italian" in SUPPORTED_LANGUAGES

    def test_synthesize_uses_italian_by_default(self):
        adapter, mock_model = _loaded_adapter()
        adapter.synthesize("Ciao mondo")
        mock_model.generate_custom_voice.assert_called_once_with(
            text="Ciao mondo",
            language="Italian",
            speaker=_DEFAULT_SPEAKER,
            instruct="",
        )


# ---------------------------------------------------------------------------
# Load / unload lifecycle
# ---------------------------------------------------------------------------

class TestQwen3TTSAdapterLoad:
    def test_load_creates_model(self):
        mock_model_cls = MagicMock()
        mock_instance = MagicMock()
        mock_model_cls.from_pretrained.return_value = mock_instance

        fake_qwen_tts = MagicMock()
        fake_qwen_tts.Qwen3TTSModel = mock_model_cls

        with patch.dict(sys.modules, {"qwen_tts": fake_qwen_tts}), \
             patch.object(Qwen3TTSAdapter, "_detect_attn_implementation", return_value=None):
            adapter = Qwen3TTSAdapter()
            adapter.load("Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice", "cuda")

        mock_model_cls.from_pretrained.assert_called_once_with(
            "Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice",
            device_map="cuda",
            dtype=torch.bfloat16,
        )
        assert adapter._model is mock_instance
        assert adapter._device == "cuda"

    def test_load_uses_flash_attention_when_available(self):
        mock_model_cls = MagicMock()
        mock_instance = MagicMock()
        mock_model_cls.from_pretrained.return_value = mock_instance

        fake_qwen_tts = MagicMock()
        fake_qwen_tts.Qwen3TTSModel = mock_model_cls

        with patch.dict(sys.modules, {"qwen_tts": fake_qwen_tts}), \
             patch.object(Qwen3TTSAdapter, "_detect_attn_implementation", return_value="flash_attention_2"):
            adapter = Qwen3TTSAdapter()
            adapter.load("Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice", "cuda")

        mock_model_cls.from_pretrained.assert_called_once_with(
            "Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice",
            device_map="cuda",
            dtype=torch.bfloat16,
            attn_implementation="flash_attention_2",
        )

    def test_unload_clears_state(self):
        adapter, _ = _loaded_adapter()
        adapter.unload()

        assert adapter._model is None
        assert adapter._device is None

    def test_unload_when_not_loaded_is_safe(self):
        adapter = Qwen3TTSAdapter()
        adapter.unload()  # Should not raise


# ---------------------------------------------------------------------------
# Synthesize
# ---------------------------------------------------------------------------

class TestQwen3TTSAdapterSynthesize:
    def test_returns_float32_numpy_array(self):
        adapter, _ = _loaded_adapter()
        audio = adapter.synthesize("Hello world")
        assert isinstance(audio, np.ndarray)
        assert audio.dtype == np.float32
        assert len(audio) > 0

    def test_returns_correct_audio_length(self):
        adapter, _ = _loaded_adapter(audio_samples=4800)
        audio = adapter.synthesize("Hello world")
        assert len(audio) == 4800

    def test_custom_speaker_passed_through(self):
        adapter, mock_model = _loaded_adapter()
        adapter.synthesize("Hello", voice="Ryan")
        mock_model.generate_custom_voice.assert_called_once_with(
            text="Hello",
            language="Italian",
            speaker="Ryan",
            instruct="",
        )

    def test_custom_language_passed_through(self):
        adapter, mock_model = _loaded_adapter()
        adapter.synthesize("Hello", language="English")
        mock_model.generate_custom_voice.assert_called_once_with(
            text="Hello",
            language="English",
            speaker=_DEFAULT_SPEAKER,
            instruct="",
        )

    def test_instruct_passed_through(self):
        adapter, mock_model = _loaded_adapter()
        adapter.synthesize("Hello", instruct="Read slowly and calmly")
        mock_model.generate_custom_voice.assert_called_once_with(
            text="Hello",
            language="Italian",
            speaker=_DEFAULT_SPEAKER,
            instruct="Read slowly and calmly",
        )

    def test_all_kwargs_combined(self):
        adapter, mock_model = _loaded_adapter()
        adapter.synthesize(
            "Ciao",
            voice="Aiden",
            language="English",
            instruct="Speak quickly",
        )
        mock_model.generate_custom_voice.assert_called_once_with(
            text="Ciao",
            language="English",
            speaker="Aiden",
            instruct="Speak quickly",
        )

    def test_empty_wavs_returns_silence(self):
        adapter, mock_model = _loaded_adapter()
        mock_model.generate_custom_voice.return_value = ([], 24000)
        audio = adapter.synthesize("...")
        assert isinstance(audio, np.ndarray)
        assert audio.dtype == np.float32
        assert len(audio) == int(24000 * 0.1)
        assert np.all(audio == 0.0)

    def test_none_wav_returns_silence(self):
        adapter, mock_model = _loaded_adapter()
        mock_model.generate_custom_voice.return_value = ([None], 24000)
        audio = adapter.synthesize("...")
        assert isinstance(audio, np.ndarray)
        assert len(audio) == int(24000 * 0.1)
        assert np.all(audio == 0.0)

    def test_empty_array_returns_silence(self):
        adapter, mock_model = _loaded_adapter()
        mock_model.generate_custom_voice.return_value = (
            [np.array([], dtype=np.float32)],
            24000,
        )
        audio = adapter.synthesize("...")
        assert isinstance(audio, np.ndarray)
        assert len(audio) == int(24000 * 0.1)

    def test_torch_tensor_converted_to_numpy(self):
        adapter, mock_model = _loaded_adapter()
        tensor_audio = torch.randn(1000)
        mock_model.generate_custom_voice.return_value = ([tensor_audio], 24000)
        audio = adapter.synthesize("Test")
        assert isinstance(audio, np.ndarray)
        assert audio.dtype == np.float32
        assert len(audio) == 1000

    def test_sample_rate_updated_from_model_output(self):
        adapter, mock_model = _loaded_adapter()
        wav = np.random.randn(1000).astype(np.float32)
        mock_model.generate_custom_voice.return_value = ([wav], 16000)
        adapter.synthesize("Test")
        assert adapter.sample_rate == 16000

    def test_synthesize_without_load_raises(self):
        adapter = Qwen3TTSAdapter()
        with pytest.raises(RuntimeError, match="load.*must be called"):
            adapter.synthesize("Hello")


# ---------------------------------------------------------------------------
# Language resolution: ISO 639-1 codes -> model language names
# ---------------------------------------------------------------------------

class TestQwen3TTSLanguageResolution:
    """The application layer speaks ISO 639-1 codes (e.g. ``it`` from the
    preprocessing pipeline / DEC-default-italian-language); the adapter maps
    them to the model's language names so synthesis does not fail with
    'Unsupported languages: [\"it\"]'."""

    def test_iso_code_it_maps_to_italian(self):
        adapter, mock_model = _loaded_adapter()
        adapter.synthesize("Ciao", language="it")
        assert mock_model.generate_custom_voice.call_args.kwargs["language"] == "Italian"

    def test_iso_code_en_maps_to_english(self):
        adapter, mock_model = _loaded_adapter()
        adapter.synthesize("Hello", language="en")
        assert mock_model.generate_custom_voice.call_args.kwargs["language"] == "English"

    def test_iso_code_is_case_insensitive(self):
        adapter, mock_model = _loaded_adapter()
        adapter.synthesize("Ciao", language="IT")
        assert mock_model.generate_custom_voice.call_args.kwargs["language"] == "Italian"

    def test_model_language_name_passes_through_any_case(self):
        adapter, mock_model = _loaded_adapter()
        adapter.synthesize("Hello", language="italian")
        assert mock_model.generate_custom_voice.call_args.kwargs["language"] == "Italian"

    def test_auto_is_accepted(self):
        adapter, mock_model = _loaded_adapter()
        adapter.synthesize("Hello", language="auto")
        assert mock_model.generate_custom_voice.call_args.kwargs["language"] == "auto"

    def test_none_falls_back_to_default(self):
        assert Qwen3TTSAdapter._resolve_language(None) == _DEFAULT_LANGUAGE
        assert Qwen3TTSAdapter._resolve_language("") == _DEFAULT_LANGUAGE

    def test_unsupported_language_raises(self):
        adapter, _ = _loaded_adapter()
        with pytest.raises(ValueError, match="Unsupported language"):
            adapter.synthesize("Hello", language="xx")


# ---------------------------------------------------------------------------
# FlashAttention detection
# ---------------------------------------------------------------------------

class TestFlashAttentionDetection:
    @patch.dict("sys.modules", {"flash_attn": MagicMock()})
    def test_returns_flash_attention_2_when_installed(self):
        result = Qwen3TTSAdapter._detect_attn_implementation()
        assert result == "flash_attention_2"

    @patch.dict("sys.modules", {"flash_attn": None})
    def test_returns_none_when_not_installed(self):
        result = Qwen3TTSAdapter._detect_attn_implementation()
        assert result is None


# ---------------------------------------------------------------------------
# Registry integration
# ---------------------------------------------------------------------------

class TestQwen3TTSAdapterRegistry:
    def test_qwen3_is_registered(self):
        """Qwen3-TTS is registered (DEC-transformers-5x-baseline): its `qwen-tts`
        package requires transformers 4.57.3, so it is usable when the exploratory
        backend baseline is installed at 4.57.3 (the version qwen-tts requires).
        The adapter is registered and lazy-imports the package (mocked in tests),
        mirroring the Fish S2-Pro pattern."""
        from local_tts.tts.adapters import has_adapter, get_adapter

        assert has_adapter("Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice") is True
        adapter = get_adapter("Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice")
        assert isinstance(adapter, Qwen3TTSAdapter)
        assert isinstance(adapter, ModelAdapter)
