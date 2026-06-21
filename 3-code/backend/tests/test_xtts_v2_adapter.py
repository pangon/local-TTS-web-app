"""Tests for the XTTS-v2 model adapter.

Covers: protocol compliance, Italian default (DEC-default-italian-language),
load/unload lifecycle via the mocked Coqui ``TTS`` low-level ``Xtts`` API loaded
from the cached snapshot, the missing-package install hint, synthesize output
coercion (dict ``{"wav": …}`` / bare array / torch tensor / silence fallback),
the built-in studio speaker path vs. the optional reference-wav cloning path
(``speaker_wav``), built-in-speaker validation/fallback, the **translate-ISO**
language handling (``it``→``it``, ``zh``→``zh-cn`` — XTTS takes an explicit
language, NOT auto-detect), local-GPU loading, registry integration, the non-FOSS
license metadata (DEC-model-license-disclosure), and the 24 kHz output pipeline.
All ``TTS`` / ``huggingface_hub`` dependencies are mocked, so the heavy GPU-host
package and the real model need not be installed (the Fish S2-Pro precedent).
"""

from __future__ import annotations

import sys
from contextlib import contextmanager
from pathlib import Path
from types import ModuleType, SimpleNamespace
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from local_tts.tts.adapters import ModelAdapter
from local_tts.tts.adapters.xtts_v2 import (
    XTTSV2Adapter,
    _DEFAULT_LANGUAGE,
    _DEFAULT_SPEAKER,
    _SAMPLE_RATE_DEFAULT,
)

_MODEL_ID = "coqui/XTTS-v2"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_model(wav=None, speakers=None) -> MagicMock:
    """Create a mock Xtts model whose ``synthesize`` returns ``{"wav": …}``."""
    model = MagicMock(name="xtts_model")
    if wav is None:
        wav = np.random.randn(4800).astype(np.float32)
    model.synthesize.return_value = {"wav": wav}
    if speakers is not None:
        model.speaker_manager.speakers = speakers
    return model


def _loaded_adapter(
    wav=None, speakers=None, sample_rate: int = 24000
) -> tuple[XTTSV2Adapter, MagicMock]:
    """Create an adapter with a mocked model ready for synthesis (no load())."""
    adapter = XTTSV2Adapter()
    adapter._model = _make_model(wav=wav, speakers=speakers)
    adapter._config = MagicMock(name="config")
    adapter._device = "cuda"
    adapter._sample_rate = sample_rate
    return adapter, adapter._model


@contextmanager
def _xtts_modules(model: MagicMock | None = None, output_sample_rate: int = 24000):
    """Patch the Coqui ``TTS`` low-level modules and ``snapshot_download``."""
    config_instance = MagicMock(name="XttsConfig_instance")
    config_instance.audio.output_sample_rate = output_sample_rate
    config_cls = MagicMock(name="XttsConfig", return_value=config_instance)

    if model is None:
        model = _make_model()
    xtts_cls = MagicMock(name="Xtts")
    xtts_cls.init_from_config.return_value = model

    cfg_mod = ModuleType("TTS.tts.configs.xtts_config")
    cfg_mod.XttsConfig = config_cls
    xtts_mod = ModuleType("TTS.tts.models.xtts")
    xtts_mod.Xtts = xtts_cls

    modules = {
        "TTS": ModuleType("TTS"),
        "TTS.tts": ModuleType("TTS.tts"),
        "TTS.tts.configs": ModuleType("TTS.tts.configs"),
        "TTS.tts.configs.xtts_config": cfg_mod,
        "TTS.tts.models": ModuleType("TTS.tts.models"),
        "TTS.tts.models.xtts": xtts_mod,
    }
    with patch.dict(sys.modules, modules), patch(
        "huggingface_hub.snapshot_download", return_value="/cache/xtts-v2"
    ):
        yield {
            "config_cls": config_cls,
            "config_instance": config_instance,
            "xtts_cls": xtts_cls,
            "model": model,
        }


# ---------------------------------------------------------------------------
# Protocol compliance
# ---------------------------------------------------------------------------

class TestXTTSV2AdapterProtocol:
    def test_satisfies_model_adapter_protocol(self):
        adapter = XTTSV2Adapter()
        assert isinstance(adapter, ModelAdapter)

    def test_default_sample_rate_is_24000(self):
        adapter = XTTSV2Adapter()
        assert adapter.sample_rate == 24000
        assert adapter.sample_rate == _SAMPLE_RATE_DEFAULT


# ---------------------------------------------------------------------------
# Default configuration (DEC-default-italian-language)
# ---------------------------------------------------------------------------

class TestXTTSV2Defaults:
    def test_default_language_is_italian(self):
        assert _DEFAULT_LANGUAGE == "it"

    def test_resolve_language_defaults_to_italian(self):
        assert XTTSV2Adapter._resolve_language(None) == "it"
        assert XTTSV2Adapter._resolve_language("") == "it"
        assert XTTSV2Adapter._resolve_language("   ") == "it"

    def test_default_speaker_is_nonempty(self):
        assert isinstance(_DEFAULT_SPEAKER, str)
        assert _DEFAULT_SPEAKER.strip()


# ---------------------------------------------------------------------------
# Load / unload lifecycle
# ---------------------------------------------------------------------------

class TestXTTSV2AdapterLoad:
    def test_load_initializes_model_from_cached_snapshot(self):
        with _xtts_modules() as mocks:
            adapter = XTTSV2Adapter()
            adapter.load(_MODEL_ID, "cuda")

        # Config loaded from the snapshot's config.json.
        mocks["config_cls"].assert_called_once()
        mocks["config_instance"].load_json.assert_called_once()
        assert mocks["config_instance"].load_json.call_args.args[0].endswith(
            "config.json"
        )

        # Model built from config and checkpoint loaded from the snapshot dir.
        mocks["xtts_cls"].init_from_config.assert_called_once_with(
            mocks["config_instance"]
        )
        load_ckpt = mocks["model"].load_checkpoint
        load_ckpt.assert_called_once()
        assert load_ckpt.call_args.kwargs["checkpoint_dir"] == "/cache/xtts-v2"
        assert load_ckpt.call_args.kwargs["eval"] is True
        assert load_ckpt.call_args.kwargs["use_deepspeed"] is False

        assert adapter._model is mocks["model"]
        assert adapter._device == "cuda"
        assert adapter.sample_rate == 24000

    def test_load_moves_model_to_requested_device(self):
        """REQ-F-synthesize-audiobook AC2: inference runs locally on the GPU."""
        with _xtts_modules() as mocks:
            adapter = XTTSV2Adapter()
            adapter.load(_MODEL_ID, "cuda")
        mocks["model"].to.assert_called_once_with("cuda")

    def test_load_reads_output_sample_rate_from_config(self):
        with _xtts_modules(output_sample_rate=22050):
            adapter = XTTSV2Adapter()
            adapter.load(_MODEL_ID, "cuda")
        assert adapter.sample_rate == 22050

    def test_read_sample_rate_falls_back_when_absent(self):
        # config without an ``audio`` attribute → default rate.
        assert XTTSV2Adapter._read_sample_rate(SimpleNamespace()) == _SAMPLE_RATE_DEFAULT
        # audio present but no output_sample_rate → default rate.
        cfg = SimpleNamespace(audio=SimpleNamespace())
        assert XTTSV2Adapter._read_sample_rate(cfg) == _SAMPLE_RATE_DEFAULT
        # explicit value honoured.
        cfg2 = SimpleNamespace(audio=SimpleNamespace(output_sample_rate=24000))
        assert XTTSV2Adapter._read_sample_rate(cfg2) == 24000

    def test_load_without_tts_raises_with_install_hint(self):
        adapter = XTTSV2Adapter()
        with patch.dict(sys.modules):
            for key in list(sys.modules):
                if key == "TTS" or key.startswith("TTS."):
                    del sys.modules[key]
            sys.modules["TTS"] = None  # force ImportError on import
            with pytest.raises(RuntimeError, match="coqui-tts"):
                adapter.load(_MODEL_ID, "cuda")

    def test_unload_clears_state(self):
        adapter, _ = _loaded_adapter()
        adapter.unload()
        assert adapter._model is None
        assert adapter._config is None
        assert adapter._device is None

    def test_unload_when_not_loaded_is_safe(self):
        adapter = XTTSV2Adapter()
        adapter.unload()  # Should not raise


# ---------------------------------------------------------------------------
# Synthesize — output coercion
# ---------------------------------------------------------------------------

class TestXTTSV2AdapterSynthesize:
    def test_returns_float32_numpy_array(self):
        adapter, _ = _loaded_adapter()
        audio = adapter.synthesize("Ciao mondo")
        assert isinstance(audio, np.ndarray)
        assert audio.dtype == np.float32
        assert len(audio) > 0

    def test_extracts_wav_from_dict(self):
        adapter, _ = _loaded_adapter(wav=np.zeros(2000, dtype=np.float32))
        audio = adapter.synthesize("Ciao")
        assert len(audio) == 2000

    def test_tolerates_bare_array_output(self):
        adapter, model = _loaded_adapter()
        model.synthesize.return_value = np.zeros(1500, dtype=np.float32)
        audio = adapter.synthesize("Ciao")
        assert len(audio) == 1500

    def test_torch_tensor_output_converted(self):
        import torch

        adapter, model = _loaded_adapter()
        model.synthesize.return_value = {"wav": torch.randn(2000)}
        audio = adapter.synthesize("Ciao")
        assert isinstance(audio, np.ndarray)
        assert audio.dtype == np.float32
        assert len(audio) == 2000

    def test_none_wav_returns_silence(self):
        adapter, model = _loaded_adapter()
        model.synthesize.return_value = {"wav": None}
        audio = adapter.synthesize("...")
        assert audio.dtype == np.float32
        assert len(audio) == int(_SAMPLE_RATE_DEFAULT * 0.1)
        assert np.all(audio == 0.0)

    def test_empty_wav_returns_silence(self):
        adapter, model = _loaded_adapter()
        model.synthesize.return_value = {"wav": np.array([], dtype=np.float32)}
        audio = adapter.synthesize("...")
        assert len(audio) == int(_SAMPLE_RATE_DEFAULT * 0.1)
        assert np.all(audio == 0.0)

    def test_text_passed_verbatim(self):
        adapter, model = _loaded_adapter()
        adapter.synthesize("Testo esatto")
        assert model.synthesize.call_args.args[0] == "Testo esatto"

    def test_modern_synthesize_api_no_deprecated_args(self):
        # coqui-tts >=0.27: only `text` is positional; `config` (deprecated) is
        # omitted and the built-in speaker uses `speaker`, not the deprecated
        # `speaker_id`.
        adapter, model = _loaded_adapter()
        adapter.synthesize("Ciao")
        assert model.synthesize.call_args.args == ("Ciao",)
        kwargs = model.synthesize.call_args.kwargs
        assert "speaker_id" not in kwargs
        assert "speaker" in kwargs

    def test_synthesize_without_load_raises(self):
        adapter = XTTSV2Adapter()
        with pytest.raises(RuntimeError, match="load.*must be called"):
            adapter.synthesize("Ciao")


# ---------------------------------------------------------------------------
# Speaker handling (built-in studio speaker vs. reference-wav cloning)
# ---------------------------------------------------------------------------

class TestXTTSV2SpeakerHandling:
    def test_default_speaker_used_when_no_voice(self):
        adapter, model = _loaded_adapter()
        adapter.synthesize("Ciao")
        kwargs = model.synthesize.call_args.kwargs
        assert kwargs["speaker"] == _DEFAULT_SPEAKER
        assert kwargs["speaker_wav"] is None

    def test_voice_kwarg_sets_built_in_speaker(self):
        adapter, model = _loaded_adapter()
        adapter.synthesize("Ciao", voice="Ana Florence")
        kwargs = model.synthesize.call_args.kwargs
        assert kwargs["speaker"] == "Ana Florence"
        assert kwargs["speaker_wav"] is None

    def test_speaker_wav_triggers_cloning(self):
        adapter, model = _loaded_adapter()
        adapter.synthesize("Ciao", speaker_wav="/ref.wav")
        kwargs = model.synthesize.call_args.kwargs
        assert kwargs["speaker_wav"] == "/ref.wav"
        assert kwargs["speaker"] is None

    def test_known_speaker_validated_against_speaker_manager(self):
        speakers = {"Ana Florence": {}, "Claribel Dervla": {}}
        adapter, model = _loaded_adapter(speakers=speakers)
        adapter.synthesize("Ciao", voice="Ana Florence")
        assert model.synthesize.call_args.kwargs["speaker"] == "Ana Florence"

    def test_unknown_speaker_falls_back_to_first_available(self):
        speakers = {"Aaa Speaker": {}, "Bbb Speaker": {}}
        adapter, model = _loaded_adapter(speakers=speakers)
        adapter.synthesize("Ciao", voice="Nonexistent Person")
        assert model.synthesize.call_args.kwargs["speaker"] == "Aaa Speaker"

    def test_speaker_passthrough_when_manager_unavailable(self):
        # speaker_manager.speakers is a MagicMock (not a dict): pass the name through.
        adapter, model = _loaded_adapter()
        adapter.synthesize("Ciao", voice="Whoever")
        assert model.synthesize.call_args.kwargs["speaker"] == "Whoever"


# ---------------------------------------------------------------------------
# Language handling (translate-ISO: XTTS takes an explicit language)
# ---------------------------------------------------------------------------

class TestXTTSV2LanguageHandling:
    """XTTS-v2 requires an explicit language, so the ISO 639-1 code is
    *translated* to the model's code (mostly identity; zh → zh-cn) and forwarded
    — unlike the auto-detect adapters (VoxCPM2 / MOSS-TTSD / Fish S2-Pro)."""

    def test_iso_it_resolves_to_it(self):
        assert XTTSV2Adapter._resolve_language("it") == "it"

    def test_iso_en_resolves_to_en(self):
        assert XTTSV2Adapter._resolve_language("en") == "en"

    def test_iso_zh_resolves_to_zh_cn(self):
        assert XTTSV2Adapter._resolve_language("zh") == "zh-cn"

    def test_native_zh_cn_accepted(self):
        assert XTTSV2Adapter._resolve_language("zh-cn") == "zh-cn"

    def test_language_is_case_insensitive(self):
        assert XTTSV2Adapter._resolve_language("IT") == "it"
        assert XTTSV2Adapter._resolve_language("ZH-CN") == "zh-cn"

    def test_language_forwarded_to_model(self):
        adapter, model = _loaded_adapter()
        adapter.synthesize("Hello", language="en")
        assert model.synthesize.call_args.kwargs["language"] == "en"

    def test_iso_zh_forwarded_as_zh_cn(self):
        adapter, model = _loaded_adapter()
        adapter.synthesize("Ni hao", language="zh")
        assert model.synthesize.call_args.kwargs["language"] == "zh-cn"

    def test_default_language_forwarded_when_omitted(self):
        adapter, model = _loaded_adapter()
        adapter.synthesize("Ciao")
        assert model.synthesize.call_args.kwargs["language"] == "it"

    def test_unsupported_language_raises(self):
        adapter, _ = _loaded_adapter()
        with pytest.raises(ValueError, match="Unsupported language"):
            adapter.synthesize("Hello", language="english")

    def test_auto_is_not_supported(self):
        # XTTS requires an explicit language — "auto" is not a valid code.
        with pytest.raises(ValueError, match="Unsupported language"):
            XTTSV2Adapter._resolve_language("auto")

    def test_malformed_language_raises(self):
        with pytest.raises(ValueError, match="Unsupported language"):
            XTTSV2Adapter._resolve_language("xx")


# ---------------------------------------------------------------------------
# Registry integration & license metadata
# ---------------------------------------------------------------------------

class TestXTTSV2AdapterRegistry:
    def test_registered_in_adapter_registry(self):
        from local_tts.tts.adapters import get_adapter, has_adapter

        assert has_adapter(_MODEL_ID) is True
        adapter = get_adapter(_MODEL_ID)
        assert adapter is not None
        assert isinstance(adapter, XTTSV2Adapter)
        assert isinstance(adapter, ModelAdapter)

    def test_in_compatible_models_as_non_foss_with_notice(self):
        from local_tts.tts.model_loader import COMPATIBLE_MODELS

        entry = COMPATIBLE_MODELS[_MODEL_ID]
        assert "CPML" in entry.license or "Coqui" in entry.license
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
# 24 kHz output pipeline (REQ-F-synthesize-audiobook AC1)
# ---------------------------------------------------------------------------

class TestXTTSV224kHzPipeline:
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
