"""Tests for the F5-TTS model adapter.

Covers: protocol compliance, Italian default (DEC-default-italian-language),
load/unload lifecycle via the mocked ``f5_tts.api.F5TTS`` class, the
missing-package install hint, synthesize output coercion (``(wav, sr, spec)``
tuple / bare array / torch tensor / 2-D flatten / silence fallback), the
reference-required behaviour (no built-in speaker) including the temporary
default-clip stopgap, the optional ``prompt_text`` (ref_text) transcript with
auto-transcription default, the **auto-detect** language handling (validated +
defaulted, advisory only — not forwarded), local-GPU loading, registry
integration, the non-FOSS (CC-BY-NC-4.0) license metadata, and the 24 kHz output
pipeline. The ``f5_tts`` dependency is mocked, so the heavy GPU-host package and
the real model need not be installed (the CosyVoice 3 / Fish S2-Pro precedent).
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
from local_tts.tts.adapters.f5_tts import (
    F5TTSAdapter,
    _DEFAULT_LANGUAGE,
    _MODEL_VARIANT,
    _SAMPLE_RATE_DEFAULT,
)

_MODEL_ID = "SWivid/F5-TTS"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_model(wav=None, sample_rate: int = 24000) -> MagicMock:
    """Create a mock F5TTS model whose ``infer`` returns ``(wav, sr, spec)``."""
    model = MagicMock(name="f5tts_model")
    if wav is None:
        wav = np.random.randn(4800).astype(np.float32)
    model.target_sample_rate = sample_rate
    model.infer.return_value = (wav, sample_rate, None)
    return model


def _loaded_adapter(
    wav=None, sample_rate: int = 24000
) -> tuple[F5TTSAdapter, MagicMock]:
    """Create an adapter with a mocked model ready for synthesis (no load())."""
    adapter = F5TTSAdapter()
    adapter._model = _make_model(wav=wav, sample_rate=sample_rate)
    adapter._device = "cuda"
    adapter._sample_rate = sample_rate
    return adapter, adapter._model


@contextmanager
def _f5tts_modules(model: MagicMock | None = None):
    """Patch the ``f5_tts.api.F5TTS`` import."""
    if model is None:
        model = _make_model()
    f5tts_cls = MagicMock(name="F5TTS", return_value=model)

    api_mod = ModuleType("f5_tts.api")
    api_mod.F5TTS = f5tts_cls

    modules = {
        "f5_tts": ModuleType("f5_tts"),
        "f5_tts.api": api_mod,
    }
    with patch.dict(sys.modules, modules):
        yield {"f5tts_cls": f5tts_cls, "model": model}


# ---------------------------------------------------------------------------
# Protocol compliance
# ---------------------------------------------------------------------------

class TestF5TTSAdapterProtocol:
    def test_satisfies_model_adapter_protocol(self):
        adapter = F5TTSAdapter()
        assert isinstance(adapter, ModelAdapter)

    def test_default_sample_rate_is_24000(self):
        adapter = F5TTSAdapter()
        assert adapter.sample_rate == 24000
        assert adapter.sample_rate == _SAMPLE_RATE_DEFAULT


# ---------------------------------------------------------------------------
# Default configuration (DEC-default-italian-language)
# ---------------------------------------------------------------------------

class TestF5TTSDefaults:
    def test_default_language_is_italian(self):
        assert _DEFAULT_LANGUAGE == "it"

    def test_resolve_language_defaults_to_italian(self):
        assert F5TTSAdapter._resolve_language(None) == "it"
        assert F5TTSAdapter._resolve_language("") == "it"
        assert F5TTSAdapter._resolve_language("   ") == "it"


# ---------------------------------------------------------------------------
# Load / unload lifecycle
# ---------------------------------------------------------------------------

class TestF5TTSAdapterLoad:
    def test_load_initializes_model_on_device(self):
        with _f5tts_modules() as mocks:
            adapter = F5TTSAdapter()
            adapter.load(_MODEL_ID, "cuda")

        mocks["f5tts_cls"].assert_called_once_with(model=_MODEL_VARIANT, device="cuda")
        assert adapter._model is mocks["model"]
        assert adapter._device == "cuda"
        assert adapter.sample_rate == 24000

    def test_load_reads_sample_rate_from_model(self):
        model = _make_model(sample_rate=22050)
        with _f5tts_modules(model=model):
            adapter = F5TTSAdapter()
            adapter.load(_MODEL_ID, "cuda")
        assert adapter.sample_rate == 22050

    def test_read_sample_rate_falls_back_when_absent(self):
        class _NoRate:
            pass

        assert F5TTSAdapter._read_sample_rate(_NoRate()) == _SAMPLE_RATE_DEFAULT

    def test_load_without_f5tts_raises_with_install_hint(self):
        adapter = F5TTSAdapter()
        with patch.dict(sys.modules):
            for key in list(sys.modules):
                if key == "f5_tts" or key.startswith("f5_tts."):
                    del sys.modules[key]
            sys.modules["f5_tts"] = None  # force ImportError on import
            with pytest.raises(RuntimeError, match="f5-tts"):
                adapter.load(_MODEL_ID, "cuda")

    def test_unload_clears_state(self):
        adapter, _ = _loaded_adapter()
        adapter.unload()
        assert adapter._model is None
        assert adapter._device is None

    def test_unload_when_not_loaded_is_safe(self):
        adapter = F5TTSAdapter()
        adapter.unload()  # Should not raise


# ---------------------------------------------------------------------------
# Synthesize — output coercion
# ---------------------------------------------------------------------------

class TestF5TTSAdapterSynthesize:
    def test_returns_float32_numpy_array(self):
        adapter, _ = _loaded_adapter()
        audio = adapter.synthesize("Ciao mondo", voice="/ref.wav")
        assert isinstance(audio, np.ndarray)
        assert audio.dtype == np.float32
        assert len(audio) > 0

    def test_wav_extracted_from_tuple(self):
        adapter, _ = _loaded_adapter(wav=np.zeros(2000, dtype=np.float32))
        audio = adapter.synthesize("Ciao", voice="/ref.wav")
        assert len(audio) == 2000

    def test_bare_array_tolerated(self):
        adapter, model = _loaded_adapter()
        model.infer.return_value = np.zeros(1500, dtype=np.float32)
        audio = adapter.synthesize("Ciao", voice="/ref.wav")
        assert len(audio) == 1500

    def test_torch_tensor_converted(self):
        import torch

        adapter, model = _loaded_adapter()
        model.infer.return_value = (torch.randn(2000), 24000, None)
        audio = adapter.synthesize("Ciao", voice="/ref.wav")
        assert isinstance(audio, np.ndarray)
        assert audio.dtype == np.float32
        assert len(audio) == 2000

    def test_2d_array_flattened(self):
        adapter, model = _loaded_adapter()
        model.infer.return_value = (np.zeros((1, 3000), dtype=np.float32), 24000, None)
        audio = adapter.synthesize("Ciao", voice="/ref.wav")
        assert audio.ndim == 1
        assert len(audio) == 3000

    def test_none_wav_returns_silence(self):
        adapter, model = _loaded_adapter()
        model.infer.return_value = (None, 24000, None)
        audio = adapter.synthesize("...", voice="/ref.wav")
        assert audio.dtype == np.float32
        assert len(audio) == int(_SAMPLE_RATE_DEFAULT * 0.1)
        assert np.all(audio == 0.0)

    def test_empty_wav_returns_silence(self):
        adapter, model = _loaded_adapter()
        model.infer.return_value = (np.array([], dtype=np.float32), 24000, None)
        audio = adapter.synthesize("...", voice="/ref.wav")
        assert len(audio) == int(_SAMPLE_RATE_DEFAULT * 0.1)

    def test_gen_text_passed_verbatim(self):
        adapter, model = _loaded_adapter()
        adapter.synthesize("Testo esatto", voice="/ref.wav")
        assert model.infer.call_args.kwargs["gen_text"] == "Testo esatto"

    def test_synthesize_without_load_raises(self):
        adapter = F5TTSAdapter()
        with pytest.raises(RuntimeError, match="load.*must be called"):
            adapter.synthesize("Ciao", voice="/ref.wav")


# ---------------------------------------------------------------------------
# Reference-clip handling (required; transcript optional; default-clip stopgap)
# ---------------------------------------------------------------------------

class TestF5TTSReferenceHandling:
    def test_missing_voice_and_no_default_raises(self, monkeypatch):
        # F5-TTS has no built-in speaker — with neither an explicit voice nor the
        # temporary default clip present, a reference is mandatory.
        monkeypatch.setattr(
            "local_tts.config.DEFAULT_VOICE_PATH",
            Path("/nonexistent/wavs/default.mp3"),
        )
        adapter, _ = _loaded_adapter()
        with pytest.raises(ValueError, match="requires a reference voice clip"):
            adapter.synthesize("Ciao")

    def test_default_clip_used_when_no_voice(self, monkeypatch, tmp_path):
        # Temporary Phase-6 stopgap: with no explicit voice, the user-provided
        # default clip (config.DEFAULT_VOICE_PATH) is used with empty ref_text.
        default = tmp_path / "default.mp3"
        default.write_bytes(b"fake-audio")
        monkeypatch.setattr("local_tts.config.DEFAULT_VOICE_PATH", default)
        adapter, model = _loaded_adapter()
        adapter.synthesize("Ciao")
        kwargs = model.infer.call_args.kwargs
        assert kwargs["ref_file"] == str(default)
        assert kwargs["ref_text"] == ""

    def test_explicit_voice_overrides_default(self, monkeypatch, tmp_path):
        default = tmp_path / "default.mp3"
        default.write_bytes(b"fake-audio")
        monkeypatch.setattr("local_tts.config.DEFAULT_VOICE_PATH", default)
        adapter, model = _loaded_adapter()
        adapter.synthesize("Ciao", voice="/ref.wav")
        assert model.infer.call_args.kwargs["ref_file"] == "/ref.wav"

    def test_voice_without_transcript_uses_empty_ref_text(self):
        # No prompt_text → empty ref_text → F5-TTS auto-transcribes the reference.
        adapter, model = _loaded_adapter()
        adapter.synthesize("Ciao", voice="/ref.wav")
        assert model.infer.call_args.kwargs["ref_text"] == ""

    def test_prompt_text_forwarded_as_ref_text(self):
        adapter, model = _loaded_adapter()
        adapter.synthesize(
            "Ciao", voice="/ref.wav", prompt_text="Testo di riferimento"
        )
        kwargs = model.infer.call_args.kwargs
        assert kwargs["ref_file"] == "/ref.wav"
        assert kwargs["ref_text"] == "Testo di riferimento"


# ---------------------------------------------------------------------------
# Language handling (auto-detect: validated + defaulted, advisory only)
# ---------------------------------------------------------------------------

class TestF5TTSLanguageHandling:
    """F5-TTS auto-detects the language from the reference and text, so the
    ISO 639-1 code is validated and defaulted but NOT forwarded — like CosyVoice
    / VoxCPM2 / MOSS-TTSD / Fish S2-Pro, NOT translated like Kokoro / XTTS."""

    def test_iso_it_accepted(self):
        assert F5TTSAdapter._resolve_language("it") == "it"

    def test_iso_en_accepted(self):
        assert F5TTSAdapter._resolve_language("en") == "en"

    def test_auto_accepted(self):
        assert F5TTSAdapter._resolve_language("auto") == "auto"

    def test_language_is_case_insensitive(self):
        assert F5TTSAdapter._resolve_language("IT") == "it"
        assert F5TTSAdapter._resolve_language("AUTO") == "auto"

    def test_language_not_forwarded_to_model(self):
        adapter, model = _loaded_adapter()
        adapter.synthesize("Ciao", voice="/ref.wav", language="en")
        # The model auto-detects: language must not appear in the inference call.
        assert "language" not in model.infer.call_args.kwargs

    def test_malformed_language_raises(self):
        with pytest.raises(ValueError, match="Unsupported language"):
            F5TTSAdapter._resolve_language("english")

    def test_malformed_language_raises_in_synthesize(self):
        adapter, _ = _loaded_adapter()
        with pytest.raises(ValueError, match="Unsupported language"):
            adapter.synthesize("Ciao", voice="/ref.wav", language="xyz")


# ---------------------------------------------------------------------------
# Registry integration & license metadata
# ---------------------------------------------------------------------------

class TestF5TTSAdapterRegistry:
    def test_registered_in_adapter_registry(self):
        from local_tts.tts.adapters import get_adapter, has_adapter

        assert has_adapter(_MODEL_ID) is True
        adapter = get_adapter(_MODEL_ID)
        assert adapter is not None
        assert isinstance(adapter, F5TTSAdapter)
        assert isinstance(adapter, ModelAdapter)

    def test_in_compatible_models_as_non_foss_with_notice(self):
        from local_tts.tts.model_loader import COMPATIBLE_MODELS

        entry = COMPATIBLE_MODELS[_MODEL_ID]
        assert entry.license_is_foss is False
        assert "CC-BY-NC" in entry.license
        # Non-FOSS models must carry a non-empty disclosure notice.
        assert entry.license_notice
        assert entry.license_notice.strip()

    def test_loader_available_via_list_models(self):
        from local_tts.tts.model_loader import ModelLoader

        with patch("local_tts.tts.model_loader.scan_cache_dir") as mock_scan:
            mock_scan.return_value = MagicMock(repos=[])
            by_id = {m.model_id: m for m in ModelLoader().list_models()}
        assert by_id[_MODEL_ID].loader_available is True
        assert by_id[_MODEL_ID].license_is_foss is False


# ---------------------------------------------------------------------------
# 24 kHz output pipeline (REQ-F-synthesize-audiobook AC1)
# ---------------------------------------------------------------------------

class TestF5TTS24kHzPipeline:
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
