"""Tests for the Kokoro-82M model adapter.

Covers: protocol compliance, load/unload lifecycle, synthesize output
format, voice and language kwargs handling, language switching, and
error handling.  All kokoro package dependencies are mocked.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock, patch

import numpy as np
import pytest
import torch

from local_tts.tts.adapters import ModelAdapter
from local_tts.tts.adapters.kokoro import KokoroAdapter, _ESPEAK_REQUIRED_LANGS, _SAMPLE_RATE


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_fake_result(audio_samples: int = 2400) -> MagicMock:
    """Create a fake KPipeline.Result with a torch audio tensor."""
    result = MagicMock()
    result.audio = torch.randn(audio_samples)
    return result


def _loaded_adapter(results: list[MagicMock] | None = None) -> KokoroAdapter:
    """Create an adapter with a mocked pipeline ready for synthesis."""
    if results is None:
        results = [_make_fake_result(2400)]
    adapter = KokoroAdapter()
    pipeline = MagicMock()
    pipeline.return_value = iter(results)
    pipeline.model = MagicMock()
    pipeline.voices = {}
    adapter._pipeline = pipeline
    adapter._model = pipeline.model
    adapter._current_lang_code = "a"
    adapter._device = "cuda"
    adapter._repo_id = "hexgrad/Kokoro-82M"
    return adapter


# ---------------------------------------------------------------------------
# Protocol compliance
# ---------------------------------------------------------------------------

class TestKokoroAdapterProtocol:
    def test_satisfies_model_adapter_protocol(self):
        adapter = KokoroAdapter()
        assert isinstance(adapter, ModelAdapter)

    def test_sample_rate_is_24000(self):
        adapter = KokoroAdapter()
        assert adapter.sample_rate == 24000
        assert adapter.sample_rate == _SAMPLE_RATE


# ---------------------------------------------------------------------------
# Load / unload lifecycle
# ---------------------------------------------------------------------------

class TestKokoroAdapterLoad:
    @patch("local_tts.tts.adapters.kokoro.shutil.which", return_value="/usr/bin/espeak-ng")
    @patch("kokoro.KPipeline")
    def test_load_creates_pipeline(self, mock_kpipeline, _mock_which):
        mock_instance = MagicMock()
        mock_instance.model = MagicMock()
        mock_instance.voices = {}
        mock_kpipeline.return_value = mock_instance

        adapter = KokoroAdapter()
        adapter.load("hexgrad/Kokoro-82M", "cuda")

        mock_kpipeline.assert_called_once_with(
            lang_code="i",
            repo_id="hexgrad/Kokoro-82M",
            device="cuda",
        )
        assert adapter._pipeline is mock_instance
        assert adapter._model is mock_instance.model

    @patch("local_tts.tts.adapters.kokoro.shutil.which", return_value="/usr/bin/espeak-ng")
    @patch("kokoro.KPipeline")
    def test_load_stores_device_and_repo(self, mock_kpipeline, _mock_which):
        mock_instance = MagicMock()
        mock_instance.model = MagicMock()
        mock_instance.voices = {}
        mock_kpipeline.return_value = mock_instance

        adapter = KokoroAdapter()
        adapter.load("hexgrad/Kokoro-82M", "cuda")

        assert adapter._device == "cuda"
        assert adapter._repo_id == "hexgrad/Kokoro-82M"
        assert adapter._current_lang_code == "i"

    @patch("local_tts.tts.adapters.kokoro.shutil.which", return_value=None)
    def test_load_checks_espeak_for_default_language(self, _mock_which):
        adapter = KokoroAdapter()
        with pytest.raises(RuntimeError, match="espeak-ng is required"):
            adapter.load("hexgrad/Kokoro-82M", "cuda")

    def test_unload_clears_state(self):
        adapter = KokoroAdapter()
        adapter._pipeline = MagicMock()
        adapter._pipeline.voices = {"test": MagicMock()}
        adapter._model = MagicMock()
        adapter._current_lang_code = "a"
        adapter._device = "cuda"
        adapter._repo_id = "hexgrad/Kokoro-82M"

        adapter.unload()

        assert adapter._pipeline is None
        assert adapter._model is None
        assert adapter._current_lang_code is None
        assert adapter._device is None
        assert adapter._repo_id is None

    def test_unload_when_not_loaded_is_safe(self):
        adapter = KokoroAdapter()
        adapter.unload()  # Should not raise


# ---------------------------------------------------------------------------
# Synthesize
# ---------------------------------------------------------------------------

class TestKokoroAdapterSynthesize:
    def test_returns_float32_numpy_array(self):
        adapter = _loaded_adapter()
        audio = adapter.synthesize("Hello world")
        assert isinstance(audio, np.ndarray)
        assert audio.dtype == np.float32
        assert len(audio) > 0

    def test_concatenates_multiple_chunks(self):
        results = [_make_fake_result(1000), _make_fake_result(2000)]
        adapter = _loaded_adapter(results)
        audio = adapter.synthesize("Hello world. This is a test.")
        assert len(audio) == 3000

    def test_default_voice_is_im_nicola(self):
        """Default voice is im_nicola (DEC-default-italian-language)."""
        adapter = _loaded_adapter()
        adapter.synthesize("Test")
        adapter._pipeline.assert_called_once_with(
            "Test", voice="im_nicola", speed=1.0,
        )

    def test_custom_voice_passed_through(self):
        adapter = _loaded_adapter()
        adapter.synthesize("Ciao", voice="if_sara")
        adapter._pipeline.assert_called_once_with(
            "Ciao", voice="if_sara", speed=1.0,
        )

    def test_custom_speed_passed_through(self):
        adapter = _loaded_adapter()
        adapter.synthesize("Fast speech", speed=1.5)
        adapter._pipeline.assert_called_once_with(
            "Fast speech", voice="im_nicola", speed=1.5,
        )

    def test_empty_result_returns_silence(self):
        adapter = _loaded_adapter(results=[])
        audio = adapter.synthesize("...")
        assert isinstance(audio, np.ndarray)
        assert audio.dtype == np.float32
        assert len(audio) == int(_SAMPLE_RATE * 0.1)
        assert np.all(audio == 0.0)

    def test_none_audio_chunks_are_skipped(self):
        good_result = _make_fake_result(1000)
        none_result = MagicMock()
        none_result.audio = None
        results = [none_result, good_result, none_result]
        adapter = _loaded_adapter(results)
        audio = adapter.synthesize("Test")
        assert len(audio) == 1000

    def test_synthesize_without_load_raises(self):
        adapter = KokoroAdapter()
        with pytest.raises(RuntimeError, match="load.*must be called"):
            adapter.synthesize("Hello")


# ---------------------------------------------------------------------------
# Language switching
# ---------------------------------------------------------------------------

class TestKokoroAdapterLanguageSwitching:
    @patch("local_tts.tts.adapters.kokoro.shutil.which", return_value="/usr/bin/espeak-ng")
    @patch("kokoro.KPipeline")
    def test_language_kwarg_switches_pipeline(self, mock_kpipeline, _mock_which):
        adapter = _loaded_adapter()
        original_model = adapter._model

        # Set up the new pipeline that will be created on language switch
        new_pipeline = MagicMock()
        new_pipeline.return_value = iter([_make_fake_result()])
        new_pipeline.voices = {}
        mock_kpipeline.return_value = new_pipeline

        adapter.synthesize("Ciao mondo", voice="if_sara", language="i")

        mock_kpipeline.assert_called_once_with(
            lang_code="i",
            repo_id="hexgrad/Kokoro-82M",
            model=original_model,
            device="cuda",
        )
        assert adapter._current_lang_code == "i"

    def test_same_language_does_not_recreate_pipeline(self):
        adapter = _loaded_adapter()
        original_pipeline = adapter._pipeline

        adapter.synthesize("Hello", language="a")

        # Pipeline should not have been replaced
        assert adapter._pipeline is original_pipeline


# ---------------------------------------------------------------------------
# espeak-ng validation
# ---------------------------------------------------------------------------

class TestEspeakValidation:
    @patch("local_tts.tts.adapters.kokoro.shutil.which", return_value=None)
    def test_raises_when_espeak_missing_for_non_english(self, _mock_which):
        with pytest.raises(RuntimeError, match="espeak-ng is required"):
            KokoroAdapter._check_espeak("i")

    @patch("local_tts.tts.adapters.kokoro.shutil.which", return_value=None)
    def test_error_message_includes_install_instructions(self, _mock_which):
        with pytest.raises(RuntimeError, match="sudo apt-get install espeak-ng"):
            KokoroAdapter._check_espeak("i")

    @patch("local_tts.tts.adapters.kokoro.shutil.which", return_value="/usr/bin/espeak-ng")
    def test_passes_when_espeak_installed(self, _mock_which):
        KokoroAdapter._check_espeak("i")  # Should not raise

    @patch("local_tts.tts.adapters.kokoro.shutil.which", return_value=None)
    def test_english_does_not_require_espeak(self, _mock_which):
        KokoroAdapter._check_espeak("a")  # Should not raise
        KokoroAdapter._check_espeak("b")  # Should not raise

    @patch("local_tts.tts.adapters.kokoro.shutil.which", return_value=None)
    def test_all_espeak_langs_are_checked(self, _mock_which):
        for lang in _ESPEAK_REQUIRED_LANGS:
            with pytest.raises(RuntimeError, match="espeak-ng is required"):
                KokoroAdapter._check_espeak(lang)

    @patch("local_tts.tts.adapters.kokoro.shutil.which", return_value=None)
    @patch("kokoro.KPipeline")
    def test_language_switch_checks_espeak(self, _mock_kpipeline, _mock_which):
        adapter = _loaded_adapter()
        with pytest.raises(RuntimeError, match="espeak-ng is required"):
            adapter.synthesize("Ciao", voice="if_sara", language="i")


# ---------------------------------------------------------------------------
# Registry integration
# ---------------------------------------------------------------------------

class TestKokoroAdapterRegistry:
    def test_kokoro_registered_in_adapter_registry(self):
        from local_tts.tts.adapters import has_adapter, get_adapter

        assert has_adapter("hexgrad/Kokoro-82M") is True
        adapter = get_adapter("hexgrad/Kokoro-82M")
        assert adapter is not None
        assert isinstance(adapter, KokoroAdapter)
        assert isinstance(adapter, ModelAdapter)
