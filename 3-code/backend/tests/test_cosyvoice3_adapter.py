"""Tests for the CosyVoice 3 model adapter.

Covers: protocol compliance, Italian default (DEC-default-italian-language),
load/unload lifecycle via the mocked ``cosyvoice`` ``AutoModel`` loaded from the
cached snapshot, the missing-package install hint, synthesize output coercion
(generator of ``{"tts_speech": …}`` chunks / torch tensor / multi-chunk concat /
silence fallback), the zero-shot vs. cross-lingual reference-clip paths, the
reference-required error (no built-in speaker), the **auto-detect** language
handling (validated + defaulted, advisory only — not forwarded), local-GPU
loading, registry integration, the Apache-2.0 (FOSS) license metadata, and the
24 kHz output pipeline. The ``cosyvoice`` / ``huggingface_hub`` dependencies are
mocked, so the heavy GPU-host package and the real model need not be installed
(the Fish S2-Pro / XTTS-v2 precedent).
"""

from __future__ import annotations

import sys
from contextlib import contextmanager
from pathlib import Path
from types import ModuleType
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from local_tts.tts.adapters import ModelAdapter
from local_tts.tts.adapters.cosyvoice3 import (
    CosyVoice3Adapter,
    _DEFAULT_LANGUAGE,
    _SAMPLE_RATE_DEFAULT,
)

_MODEL_ID = "FunAudioLLM/Fun-CosyVoice3-0.5B-2512"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _speech_generator(*chunks):
    """A generator yielding ``{"tts_speech": chunk}`` dicts (the CosyVoice API)."""
    def _gen():
        for chunk in chunks:
            yield {"tts_speech": chunk}
    return _gen()


def _make_model(chunks=None, sample_rate: int = 24000) -> MagicMock:
    """Create a mock CosyVoice AutoModel whose inference methods yield chunks."""
    model = MagicMock(name="cosyvoice_model")
    if chunks is None:
        chunks = (np.random.randn(4800).astype(np.float32),)
    model.sample_rate = sample_rate
    model.inference_zero_shot.return_value = _speech_generator(*chunks)
    model.inference_cross_lingual.return_value = _speech_generator(*chunks)
    return model


def _loaded_adapter(
    chunks=None, sample_rate: int = 24000
) -> tuple[CosyVoice3Adapter, MagicMock]:
    """Create an adapter with a mocked model ready for synthesis (no load())."""
    adapter = CosyVoice3Adapter()
    adapter._model = _make_model(chunks=chunks, sample_rate=sample_rate)
    adapter._device = "cuda"
    adapter._sample_rate = sample_rate
    return adapter, adapter._model


@contextmanager
def _cosyvoice_modules(model: MagicMock | None = None):
    """Patch the ``cosyvoice.cli.cosyvoice.AutoModel`` import and snapshot_download."""
    if model is None:
        model = _make_model()
    auto_model_cls = MagicMock(name="AutoModel", return_value=model)

    cli_mod = ModuleType("cosyvoice.cli.cosyvoice")
    cli_mod.AutoModel = auto_model_cls

    modules = {
        "cosyvoice": ModuleType("cosyvoice"),
        "cosyvoice.cli": ModuleType("cosyvoice.cli"),
        "cosyvoice.cli.cosyvoice": cli_mod,
    }
    with patch.dict(sys.modules, modules), patch(
        "huggingface_hub.snapshot_download", return_value="/cache/cosyvoice3"
    ):
        yield {"auto_model_cls": auto_model_cls, "model": model}


# ---------------------------------------------------------------------------
# Protocol compliance
# ---------------------------------------------------------------------------

class TestCosyVoice3AdapterProtocol:
    def test_satisfies_model_adapter_protocol(self):
        adapter = CosyVoice3Adapter()
        assert isinstance(adapter, ModelAdapter)

    def test_default_sample_rate_is_24000(self):
        adapter = CosyVoice3Adapter()
        assert adapter.sample_rate == 24000
        assert adapter.sample_rate == _SAMPLE_RATE_DEFAULT


# ---------------------------------------------------------------------------
# Default configuration (DEC-default-italian-language)
# ---------------------------------------------------------------------------

class TestCosyVoice3Defaults:
    def test_default_language_is_italian(self):
        assert _DEFAULT_LANGUAGE == "it"

    def test_resolve_language_defaults_to_italian(self):
        assert CosyVoice3Adapter._resolve_language(None) == "it"
        assert CosyVoice3Adapter._resolve_language("") == "it"
        assert CosyVoice3Adapter._resolve_language("   ") == "it"


# ---------------------------------------------------------------------------
# Load / unload lifecycle
# ---------------------------------------------------------------------------

class TestCosyVoice3AdapterLoad:
    def test_load_initializes_model_from_cached_snapshot(self):
        with _cosyvoice_modules() as mocks:
            adapter = CosyVoice3Adapter()
            adapter.load(_MODEL_ID, "cuda")

        mocks["auto_model_cls"].assert_called_once_with(model_dir="/cache/cosyvoice3")
        assert adapter._model is mocks["model"]
        assert adapter._device == "cuda"
        assert adapter.sample_rate == 24000

    def test_load_reads_sample_rate_from_model(self):
        model = _make_model(sample_rate=22050)
        with _cosyvoice_modules(model=model):
            adapter = CosyVoice3Adapter()
            adapter.load(_MODEL_ID, "cuda")
        assert adapter.sample_rate == 22050

    def test_read_sample_rate_falls_back_when_absent(self):
        class _NoRate:
            pass

        assert CosyVoice3Adapter._read_sample_rate(_NoRate()) == _SAMPLE_RATE_DEFAULT

    def test_load_without_cosyvoice_raises_with_install_hint(self):
        adapter = CosyVoice3Adapter()
        with patch.dict(sys.modules):
            for key in list(sys.modules):
                if key == "cosyvoice" or key.startswith("cosyvoice."):
                    del sys.modules[key]
            sys.modules["cosyvoice"] = None  # force ImportError on import
            with pytest.raises(RuntimeError, match="cosyvoice"):
                adapter.load(_MODEL_ID, "cuda")

    def test_unload_clears_state(self):
        adapter, _ = _loaded_adapter()
        adapter.unload()
        assert adapter._model is None
        assert adapter._device is None

    def test_unload_when_not_loaded_is_safe(self):
        adapter = CosyVoice3Adapter()
        adapter.unload()  # Should not raise


# ---------------------------------------------------------------------------
# Synthesize — output coercion
# ---------------------------------------------------------------------------

class TestCosyVoice3AdapterSynthesize:
    def test_returns_float32_numpy_array(self):
        adapter, _ = _loaded_adapter()
        audio = adapter.synthesize("Ciao mondo", voice="/ref.wav")
        assert isinstance(audio, np.ndarray)
        assert audio.dtype == np.float32
        assert len(audio) > 0

    def test_single_chunk_extracted(self):
        adapter, _ = _loaded_adapter(chunks=(np.zeros(2000, dtype=np.float32),))
        audio = adapter.synthesize("Ciao", voice="/ref.wav")
        assert len(audio) == 2000

    def test_multiple_chunks_concatenated(self):
        chunks = (
            np.zeros(1000, dtype=np.float32),
            np.ones(500, dtype=np.float32),
        )
        adapter, _ = _loaded_adapter(chunks=chunks)
        audio = adapter.synthesize("Ciao", voice="/ref.wav")
        assert len(audio) == 1500

    def test_torch_tensor_chunk_converted(self):
        import torch

        adapter, model = _loaded_adapter()
        model.inference_cross_lingual.return_value = _speech_generator(torch.randn(2000))
        audio = adapter.synthesize("Ciao", voice="/ref.wav")
        assert isinstance(audio, np.ndarray)
        assert audio.dtype == np.float32
        assert len(audio) == 2000

    def test_2d_tensor_chunk_flattened(self):
        import torch

        adapter, model = _loaded_adapter()
        model.inference_cross_lingual.return_value = _speech_generator(torch.randn(1, 3000))
        audio = adapter.synthesize("Ciao", voice="/ref.wav")
        assert audio.ndim == 1
        assert len(audio) == 3000

    def test_empty_generator_returns_silence(self):
        adapter, model = _loaded_adapter()
        model.inference_cross_lingual.return_value = _speech_generator()
        audio = adapter.synthesize("...", voice="/ref.wav")
        assert audio.dtype == np.float32
        assert len(audio) == int(_SAMPLE_RATE_DEFAULT * 0.1)
        assert np.all(audio == 0.0)

    def test_none_chunk_skipped_returns_silence(self):
        adapter, model = _loaded_adapter()
        model.inference_cross_lingual.return_value = _speech_generator(None)
        audio = adapter.synthesize("...", voice="/ref.wav")
        assert len(audio) == int(_SAMPLE_RATE_DEFAULT * 0.1)

    def test_text_passed_verbatim(self):
        adapter, model = _loaded_adapter()
        adapter.synthesize("Testo esatto", voice="/ref.wav")
        assert model.inference_cross_lingual.call_args.args[0] == "Testo esatto"

    def test_synthesize_without_load_raises(self):
        adapter = CosyVoice3Adapter()
        with pytest.raises(RuntimeError, match="load.*must be called"):
            adapter.synthesize("Ciao", voice="/ref.wav")


# ---------------------------------------------------------------------------
# Reference-clip handling (zero-shot vs cross-lingual; reference required)
# ---------------------------------------------------------------------------

class TestCosyVoice3ReferenceHandling:
    def test_missing_voice_and_no_default_raises(self, monkeypatch):
        # CosyVoice 3 has no built-in speaker — with neither an explicit voice nor
        # the temporary default clip present, a reference is mandatory.
        monkeypatch.setattr(
            "local_tts.config.DEFAULT_VOICE_PATH",
            Path("/nonexistent/wavs/default.mp3"),
        )
        adapter, _ = _loaded_adapter()
        with pytest.raises(ValueError, match="requires a reference voice clip"):
            adapter.synthesize("Ciao")

    def test_default_clip_used_when_no_voice(self, monkeypatch, tmp_path):
        # Temporary Phase-6 stopgap: with no explicit voice, the user-provided
        # default clip (config.DEFAULT_VOICE_PATH) is used via cross-lingual.
        default = tmp_path / "default.mp3"
        default.write_bytes(b"fake-audio")
        monkeypatch.setattr("local_tts.config.DEFAULT_VOICE_PATH", default)
        adapter, model = _loaded_adapter()
        adapter.synthesize("Ciao")
        model.inference_cross_lingual.assert_called_once()
        model.inference_zero_shot.assert_not_called()
        assert model.inference_cross_lingual.call_args.args == ("Ciao", str(default))

    def test_explicit_voice_overrides_default(self, monkeypatch, tmp_path):
        default = tmp_path / "default.mp3"
        default.write_bytes(b"fake-audio")
        monkeypatch.setattr("local_tts.config.DEFAULT_VOICE_PATH", default)
        adapter, model = _loaded_adapter()
        adapter.synthesize("Ciao", voice="/ref.wav")
        assert model.inference_cross_lingual.call_args.args == ("Ciao", "/ref.wav")

    def test_voice_only_uses_cross_lingual(self):
        adapter, model = _loaded_adapter()
        adapter.synthesize("Ciao", voice="/ref.wav")
        model.inference_cross_lingual.assert_called_once()
        model.inference_zero_shot.assert_not_called()
        args = model.inference_cross_lingual.call_args
        assert args.args == ("Ciao", "/ref.wav")
        assert args.kwargs.get("stream") is False

    def test_voice_and_prompt_text_uses_zero_shot(self):
        adapter, model = _loaded_adapter()
        adapter.synthesize("Ciao", voice="/ref.wav", prompt_text="Testo di riferimento")
        model.inference_zero_shot.assert_called_once()
        model.inference_cross_lingual.assert_not_called()
        args = model.inference_zero_shot.call_args
        assert args.args == ("Ciao", "Testo di riferimento", "/ref.wav")
        assert args.kwargs.get("stream") is False


# ---------------------------------------------------------------------------
# Language handling (auto-detect: validated + defaulted, advisory only)
# ---------------------------------------------------------------------------

class TestCosyVoice3LanguageHandling:
    """CosyVoice 3 auto-detects the language from the text, so the ISO 639-1
    code is validated and defaulted but NOT forwarded — like VoxCPM2 / MOSS-TTSD
    / Fish S2-Pro, NOT translated-and-forwarded like Kokoro / Qwen3 / XTTS."""

    def test_iso_it_accepted(self):
        assert CosyVoice3Adapter._resolve_language("it") == "it"

    def test_iso_en_accepted(self):
        assert CosyVoice3Adapter._resolve_language("en") == "en"

    def test_auto_accepted(self):
        assert CosyVoice3Adapter._resolve_language("auto") == "auto"

    def test_language_is_case_insensitive(self):
        assert CosyVoice3Adapter._resolve_language("IT") == "it"
        assert CosyVoice3Adapter._resolve_language("AUTO") == "auto"

    def test_language_not_forwarded_to_model(self):
        adapter, model = _loaded_adapter()
        adapter.synthesize("Ciao", voice="/ref.wav", language="en")
        # The model auto-detects: language must not appear in the inference call.
        assert "language" not in model.inference_cross_lingual.call_args.kwargs

    def test_malformed_language_raises(self):
        with pytest.raises(ValueError, match="Unsupported language"):
            CosyVoice3Adapter._resolve_language("english")

    def test_malformed_language_raises_in_synthesize(self):
        adapter, _ = _loaded_adapter()
        with pytest.raises(ValueError, match="Unsupported language"):
            adapter.synthesize("Ciao", voice="/ref.wav", language="xyz")


# ---------------------------------------------------------------------------
# Registry integration & license metadata
# ---------------------------------------------------------------------------

class TestCosyVoice3AdapterRegistry:
    def test_registered_in_adapter_registry(self):
        from local_tts.tts.adapters import get_adapter, has_adapter

        assert has_adapter(_MODEL_ID) is True
        adapter = get_adapter(_MODEL_ID)
        assert adapter is not None
        assert isinstance(adapter, CosyVoice3Adapter)
        assert isinstance(adapter, ModelAdapter)

    def test_in_compatible_models_as_foss(self):
        from local_tts.tts.model_loader import COMPATIBLE_MODELS

        entry = COMPATIBLE_MODELS[_MODEL_ID]
        assert entry.license_is_foss is True
        assert "Apache" in entry.license
        assert entry.license_notice is None  # FOSS models carry no notice

    def test_loader_available_via_list_models(self):
        from local_tts.tts.model_loader import ModelLoader

        with patch("local_tts.tts.model_loader.scan_cache_dir") as mock_scan:
            mock_scan.return_value = MagicMock(repos=[])
            by_id = {m.model_id: m for m in ModelLoader().list_models()}
        assert by_id[_MODEL_ID].loader_available is True
        assert by_id[_MODEL_ID].license_is_foss is True


# ---------------------------------------------------------------------------
# 24 kHz output pipeline (REQ-F-synthesize-audiobook AC1)
# ---------------------------------------------------------------------------

class TestCosyVoice324kHzPipeline:
    def test_encode_to_mp3_handles_24000(self, tmp_path: Path):
        """The synthesizer reads the rate from the adapter and pydub/ffmpeg
        encode it, so the 24 kHz output produces a valid MP3 covering the text."""
        from local_tts.tts.synthesizer import encode_to_mp3

        waveform = np.random.randn(_SAMPLE_RATE_DEFAULT).astype(np.float32) * 0.1
        out = tmp_path / "chapter-01.mp3"
        duration = encode_to_mp3(waveform, _SAMPLE_RATE_DEFAULT, out)

        assert out.exists()
        assert out.stat().st_size > 0
        assert duration == pytest.approx(1.0, abs=0.1)
