"""Tests for the Fish Audio S2-Pro model adapter.

Covers: protocol compliance, Italian default (DEC-default-italian-language),
load/unload lifecycle via mocked fish-speech engine helpers, the missing-package
install hint, synthesize output coercion + segment/final selection, the
confirmed-text guarantee (normalize=False, DEC-preprocess-review-flow), the
optional reference-audio voice-cloning path, the advisory auto-detected language
handling (no language tag is forwarded — like VoxCPM2/MOSS-TTSD), registry
integration, the non-FOSS license metadata (DEC-model-license-disclosure), and
the 44.1 kHz output pipeline.  All ``fish-speech`` / ``huggingface_hub``
dependencies are mocked, so the GitHub-only package and ~5B model need not be
installed.
"""

from __future__ import annotations

import sys
from contextlib import contextmanager
from pathlib import Path
from types import ModuleType
from unittest.mock import MagicMock, patch

import numpy as np
import pytest
import torch

from local_tts.tts.adapters import ModelAdapter
from local_tts.tts.adapters.fish_s2_pro import (
    FishS2ProAdapter,
    _DEFAULT_LANGUAGE,
    _SAMPLE_RATE_DEFAULT,
)

_MODEL_ID = "fishaudio/s2-pro"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _result(code: str, audio=None, error=None) -> MagicMock:
    """Create a mock InferenceResult with the published fields."""
    r = MagicMock()
    r.code = code
    r.audio = audio
    r.error = error
    return r


def _loaded_adapter(
    results: list | None = None, audio_samples: int = 4800
) -> tuple[FishS2ProAdapter, MagicMock]:
    """Create an adapter with a mocked engine ready for synthesis."""
    adapter = FishS2ProAdapter()
    engine = MagicMock()
    if results is None:
        results = [
            _result(
                "segment",
                (44100, np.random.randn(audio_samples).astype(np.float32)),
            )
        ]
    engine.inference.return_value = results
    adapter._engine = engine
    adapter._device = "cuda"
    adapter._sample_rate = 44100
    return adapter, engine


@contextmanager
def _fish_schema():
    """Patch ``fish_speech.utils.schema`` with mock request/reference classes."""
    root = ModuleType("fish_speech")
    utils = ModuleType("fish_speech.utils")
    schema = ModuleType("fish_speech.utils.schema")
    schema.ServeTTSRequest = MagicMock(name="ServeTTSRequest")
    schema.ServeReferenceAudio = MagicMock(name="ServeReferenceAudio")
    with patch.dict(
        sys.modules,
        {
            "fish_speech": root,
            "fish_speech.utils": utils,
            "fish_speech.utils.schema": schema,
        },
    ):
        yield schema


@contextmanager
def _fish_load_modules(decoder: MagicMock | None = None):
    """Patch all fish-speech load-time modules and ``snapshot_download``."""
    engine_cls = MagicMock(name="TTSInferenceEngine")
    engine_cls.return_value = MagicMock(name="engine_instance")
    launch = MagicMock(name="launch_thread_safe_queue", return_value=MagicMock())
    if decoder is None:
        decoder = MagicMock()
        decoder.sample_rate = 44100
    load_dec = MagicMock(name="load_decoder_model", return_value=decoder)

    ie_mod = ModuleType("fish_speech.inference_engine")
    ie_mod.TTSInferenceEngine = engine_cls
    dac_mod = ModuleType("fish_speech.models.dac.inference")
    dac_mod.load_model = load_dec
    t2s_mod = ModuleType("fish_speech.models.text2semantic.inference")
    t2s_mod.launch_thread_safe_queue = launch

    modules = {
        "fish_speech": ModuleType("fish_speech"),
        "fish_speech.inference_engine": ie_mod,
        "fish_speech.models": ModuleType("fish_speech.models"),
        "fish_speech.models.dac": ModuleType("fish_speech.models.dac"),
        "fish_speech.models.dac.inference": dac_mod,
        "fish_speech.models.text2semantic": ModuleType(
            "fish_speech.models.text2semantic"
        ),
        "fish_speech.models.text2semantic.inference": t2s_mod,
    }
    with patch.dict(sys.modules, modules), patch(
        "huggingface_hub.snapshot_download", return_value="/cache/s2-pro"
    ):
        yield {"engine_cls": engine_cls, "launch": launch, "load_dec": load_dec}


# ---------------------------------------------------------------------------
# Protocol compliance
# ---------------------------------------------------------------------------

class TestFishS2ProAdapterProtocol:
    def test_satisfies_model_adapter_protocol(self):
        adapter = FishS2ProAdapter()
        assert isinstance(adapter, ModelAdapter)

    def test_default_sample_rate_is_44100(self):
        adapter = FishS2ProAdapter()
        assert adapter.sample_rate == 44100
        assert adapter.sample_rate == _SAMPLE_RATE_DEFAULT


# ---------------------------------------------------------------------------
# Default configuration (DEC-default-italian-language)
# ---------------------------------------------------------------------------

class TestFishS2ProDefaults:
    def test_default_language_is_italian(self):
        assert _DEFAULT_LANGUAGE == "it"

    def test_resolve_language_defaults_to_italian(self):
        assert FishS2ProAdapter._resolve_language(None) == "it"
        assert FishS2ProAdapter._resolve_language("") == "it"
        assert FishS2ProAdapter._resolve_language("   ") == "it"


# ---------------------------------------------------------------------------
# Load / unload lifecycle
# ---------------------------------------------------------------------------

class TestFishS2ProAdapterLoad:
    def test_load_builds_engine_from_queue_and_decoder(self):
        with _fish_load_modules() as mocks:
            adapter = FishS2ProAdapter()
            adapter.load(_MODEL_ID, "cuda")

        mocks["launch"].assert_called_once()
        assert mocks["launch"].call_args.kwargs["checkpoint_path"] == "/cache/s2-pro"
        assert mocks["launch"].call_args.kwargs["device"] == "cuda"
        assert mocks["launch"].call_args.kwargs["precision"] == torch.bfloat16

        mocks["load_dec"].assert_called_once()
        assert mocks["load_dec"].call_args.kwargs["checkpoint_path"].endswith(
            "codec.pth"
        )
        assert mocks["load_dec"].call_args.kwargs["device"] == "cuda"

        mocks["engine_cls"].assert_called_once()
        assert adapter._engine is mocks["engine_cls"].return_value
        assert adapter._device == "cuda"
        assert adapter.sample_rate == 44100

    def test_load_reads_sample_rate_from_decoder(self):
        decoder = MagicMock()
        decoder.sample_rate = 24000
        with _fish_load_modules(decoder=decoder):
            adapter = FishS2ProAdapter()
            adapter.load(_MODEL_ID, "cuda")
        assert adapter.sample_rate == 24000

    def test_load_falls_back_to_default_sample_rate(self):
        decoder = MagicMock(spec=[])  # no sample_rate / sampling_rate attrs
        with _fish_load_modules(decoder=decoder):
            adapter = FishS2ProAdapter()
            adapter.load(_MODEL_ID, "cuda")
        assert adapter.sample_rate == _SAMPLE_RATE_DEFAULT

    def test_load_without_fish_speech_raises_with_install_hint(self):
        adapter = FishS2ProAdapter()
        with patch.dict(sys.modules):
            for key in list(sys.modules):
                if key == "fish_speech" or key.startswith("fish_speech."):
                    del sys.modules[key]
            sys.modules["fish_speech"] = None  # force ImportError on import
            with pytest.raises(RuntimeError, match="fish-speech"):
                adapter.load(_MODEL_ID, "cuda")

    def test_unload_clears_state(self):
        adapter, _ = _loaded_adapter()
        adapter.unload()
        assert adapter._engine is None
        assert adapter._device is None

    def test_unload_when_not_loaded_is_safe(self):
        adapter = FishS2ProAdapter()
        adapter.unload()  # Should not raise


# ---------------------------------------------------------------------------
# Synthesize
# ---------------------------------------------------------------------------

class TestFishS2ProAdapterSynthesize:
    def test_returns_float32_numpy_array(self):
        adapter, _ = _loaded_adapter()
        with _fish_schema():
            audio = adapter.synthesize("Ciao mondo")
        assert isinstance(audio, np.ndarray)
        assert audio.dtype == np.float32
        assert len(audio) > 0

    def test_concatenates_multiple_segments(self):
        results = [
            _result("segment", (44100, np.zeros(1000, dtype=np.float32))),
            _result("segment", (44100, np.zeros(1500, dtype=np.float32))),
        ]
        adapter, _ = _loaded_adapter(results=results)
        with _fish_schema():
            audio = adapter.synthesize("Ciao")
        assert len(audio) == 2500

    def test_prefers_segments_over_final_to_avoid_double_count(self):
        full = np.zeros(2500, dtype=np.float32)
        results = [
            _result("segment", (44100, np.zeros(1000, dtype=np.float32))),
            _result("segment", (44100, np.zeros(1500, dtype=np.float32))),
            _result("final", (44100, full)),
        ]
        adapter, _ = _loaded_adapter(results=results)
        with _fish_schema():
            audio = adapter.synthesize("Ciao")
        assert len(audio) == 2500  # segments only, final not added on top

    def test_falls_back_to_final_when_no_segments(self):
        results = [
            _result("header", None),
            _result("final", (44100, np.zeros(3000, dtype=np.float32))),
        ]
        adapter, _ = _loaded_adapter(results=results)
        with _fish_schema():
            audio = adapter.synthesize("Ciao")
        assert len(audio) == 3000

    def test_error_result_raises(self):
        results = [_result("error", None, error="boom")]
        adapter, _ = _loaded_adapter(results=results)
        with _fish_schema():
            with pytest.raises(RuntimeError, match="boom"):
                adapter.synthesize("Ciao")

    def test_reads_sample_rate_from_result(self):
        results = [_result("segment", (22050, np.zeros(1000, dtype=np.float32)))]
        adapter, _ = _loaded_adapter(results=results)
        with _fish_schema():
            adapter.synthesize("Ciao")
        assert adapter.sample_rate == 22050

    def test_no_audio_returns_silence(self):
        results = [_result("header", None), _result("final", None)]
        adapter, _ = _loaded_adapter(results=results)
        with _fish_schema():
            audio = adapter.synthesize("...")
        assert isinstance(audio, np.ndarray)
        assert audio.dtype == np.float32
        assert len(audio) == int(_SAMPLE_RATE_DEFAULT * 0.1)
        assert np.all(audio == 0.0)

    def test_torch_tensor_segment_converted(self):
        results = [_result("segment", (44100, torch.randn(2000)))]
        adapter, _ = _loaded_adapter(results=results)
        with _fish_schema():
            audio = adapter.synthesize("Ciao")
        assert isinstance(audio, np.ndarray)
        assert audio.dtype == np.float32
        assert len(audio) == 2000

    def test_does_not_renormalize_confirmed_text(self):
        """normalize must be False so the exact confirmed text is spoken
        (DEC-preprocess-review-flow); ServeTTSRequest defaults it to True."""
        adapter, _ = _loaded_adapter()
        with _fish_schema() as schema:
            adapter.synthesize("1.234,56")
        assert schema.ServeTTSRequest.call_args.kwargs["normalize"] is False

    def test_text_passed_verbatim(self):
        adapter, _ = _loaded_adapter()
        with _fish_schema() as schema:
            adapter.synthesize("Testo esatto")
        assert schema.ServeTTSRequest.call_args.kwargs["text"] == "Testo esatto"

    def test_no_references_without_voice(self):
        adapter, _ = _loaded_adapter()
        with _fish_schema() as schema:
            adapter.synthesize("Ciao")
        assert schema.ServeTTSRequest.call_args.kwargs["references"] == []

    def test_reference_audio_voice_built_from_clip(self, tmp_path: Path):
        ref = tmp_path / "ref.wav"
        ref.write_bytes(b"RIFFfakewav")
        adapter, _ = _loaded_adapter()
        with _fish_schema() as schema:
            adapter.synthesize("Ciao", voice=str(ref), prompt_text="Riferimento")
        schema.ServeReferenceAudio.assert_called_once_with(
            audio=b"RIFFfakewav", text="Riferimento"
        )
        refs = schema.ServeTTSRequest.call_args.kwargs["references"]
        assert refs == [schema.ServeReferenceAudio.return_value]

    def test_max_new_tokens_passed_through(self):
        adapter, _ = _loaded_adapter()
        with _fish_schema() as schema:
            adapter.synthesize("Ciao", max_new_tokens=512)
        assert schema.ServeTTSRequest.call_args.kwargs["max_new_tokens"] == 512

    def test_synthesize_without_load_raises(self):
        adapter = FishS2ProAdapter()
        with pytest.raises(RuntimeError, match="load.*must be called"):
            adapter.synthesize("Ciao")


# ---------------------------------------------------------------------------
# Language handling (advisory: S2-Pro auto-detects; kwarg is validated only)
# ---------------------------------------------------------------------------

class TestFishS2ProLanguageHandling:
    """S2-Pro auto-detects the language from the text, so the ISO 639-1
    ``language`` kwarg is validated and defaulted to Italian but is NOT passed
    to the model (ServeTTSRequest has no language field)."""

    def test_iso_code_it_accepted_and_not_forwarded(self):
        adapter, _ = _loaded_adapter()
        with _fish_schema() as schema:
            adapter.synthesize("Ciao", language="it")
        assert "language" not in schema.ServeTTSRequest.call_args.kwargs

    def test_iso_code_en_accepted(self):
        adapter, _ = _loaded_adapter()
        with _fish_schema():
            adapter.synthesize("Hello", language="en")  # Should not raise

    def test_iso_code_is_case_insensitive(self):
        assert FishS2ProAdapter._resolve_language("IT") == "it"

    def test_auto_is_accepted(self):
        assert FishS2ProAdapter._resolve_language("auto") == "auto"

    def test_unsupported_language_raises(self):
        adapter, _ = _loaded_adapter()
        with _fish_schema():
            with pytest.raises(ValueError, match="Unsupported language"):
                adapter.synthesize("Hello", language="english")

    def test_malformed_language_raises(self):
        with pytest.raises(ValueError, match="Unsupported language"):
            FishS2ProAdapter._resolve_language("123")


# ---------------------------------------------------------------------------
# Registry integration & license metadata
# ---------------------------------------------------------------------------

class TestFishS2ProAdapterRegistry:
    def test_registered_in_adapter_registry(self):
        from local_tts.tts.adapters import get_adapter, has_adapter

        assert has_adapter(_MODEL_ID) is True
        adapter = get_adapter(_MODEL_ID)
        assert adapter is not None
        assert isinstance(adapter, FishS2ProAdapter)
        assert isinstance(adapter, ModelAdapter)

    def test_in_compatible_models_as_non_foss_with_notice(self):
        from local_tts.tts.model_loader import COMPATIBLE_MODELS

        entry = COMPATIBLE_MODELS[_MODEL_ID]
        assert entry.license == "Fish Audio Research License"
        assert entry.license_is_foss is False
        assert entry.license_notice  # non-empty disclosure (DEC-model-license-disclosure)
        assert "commercial" in entry.license_notice.lower()

    def test_loader_available_via_list_models(self):
        from local_tts.tts.model_loader import ModelLoader

        with patch("local_tts.tts.model_loader.scan_cache_dir") as mock_scan:
            mock_scan.return_value = MagicMock(repos=[])
            by_id = {m.model_id: m for m in ModelLoader().list_models()}
        assert by_id[_MODEL_ID].loader_available is True
        assert by_id[_MODEL_ID].license_is_foss is False
        assert by_id[_MODEL_ID].license_notice


# ---------------------------------------------------------------------------
# 44.1 kHz output pipeline
# ---------------------------------------------------------------------------

class TestFishS2Pro44kHzPipeline:
    def test_encode_to_mp3_handles_44100(self, tmp_path: Path):
        """The synthesizer reads the rate from the adapter and pydub/ffmpeg
        encode any rate, so the 44.1 kHz output needs no special handling."""
        from local_tts.tts.synthesizer import encode_to_mp3

        waveform = np.random.randn(_SAMPLE_RATE_DEFAULT).astype(np.float32) * 0.1
        out = tmp_path / "chapter-01.mp3"
        duration = encode_to_mp3(waveform, _SAMPLE_RATE_DEFAULT, out)

        assert out.exists()
        assert out.stat().st_size > 0
        assert duration == pytest.approx(1.0, abs=0.1)
