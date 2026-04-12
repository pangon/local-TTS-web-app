"""Tests for the TTSEngine unified interface.

Covers: GPU validation delegation, model management delegation, chapter
parsing delegation, synthesis orchestration, and independence from web
framework. All GPU/model dependencies are mocked.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from local_tts.tts.engine import TTSEngine
from local_tts.tts.gpu_validator import GPUInfo, GPUValidationError, VRAMCheckResult
from local_tts.tts.model_loader import DiskSpaceCheck, ModelInfo, ModelLoadError
from local_tts.tts.synthesizer import SynthesisError, SynthesisResult


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def engine() -> TTSEngine:
    return TTSEngine()


# ---------------------------------------------------------------------------
# GPU validation
# ---------------------------------------------------------------------------

class TestValidateGPU:
    @patch("local_tts.tts.engine.validate_gpu")
    def test_delegates_to_gpu_validator(self, mock_validate, engine):
        gpu_info = GPUInfo(
            name="RTX 3080", vram_total_mb=10240.0,
            vram_free_mb=8192.0, cuda_version="12.1",
        )
        mock_validate.return_value = gpu_info
        result = engine.validate_gpu()
        assert result == gpu_info
        mock_validate.assert_called_once()

    @patch("local_tts.tts.engine.validate_gpu")
    def test_raises_on_no_gpu(self, mock_validate, engine):
        mock_validate.side_effect = GPUValidationError("No GPU")
        with pytest.raises(GPUValidationError, match="No GPU"):
            engine.validate_gpu()


class TestGetGPUStatus:
    @patch("local_tts.tts.engine.get_gpu_status")
    def test_returns_gpu_info(self, mock_status, engine):
        gpu_info = GPUInfo(
            name="RTX 3080", vram_total_mb=10240.0,
            vram_free_mb=8192.0, cuda_version="12.1",
        )
        mock_status.return_value = gpu_info
        assert engine.get_gpu_status() == gpu_info

    @patch("local_tts.tts.engine.get_gpu_status")
    def test_returns_none_when_no_gpu(self, mock_status, engine):
        mock_status.return_value = None
        assert engine.get_gpu_status() is None


class TestCheckVRAM:
    @patch("local_tts.tts.engine.check_vram")
    def test_delegates_to_gpu_validator(self, mock_check, engine):
        result = VRAMCheckResult(sufficient=True, required_mb=500.0, available_mb=8192.0)
        mock_check.return_value = result
        assert engine.check_vram(500.0) == result
        mock_check.assert_called_once_with(500.0)


# ---------------------------------------------------------------------------
# Model management
# ---------------------------------------------------------------------------

class TestLoadedModelId:
    def test_initially_none(self, engine):
        assert engine.loaded_model_id is None


class TestListModels:
    @patch.object(TTSEngine, "_model_loader", create=True)
    def test_delegates_to_model_loader(self, mock_loader, engine):
        models = [ModelInfo("facebook/mms-tts-eng", "MMS TTS English", True, False, False)]
        engine._model_loader = MagicMock()
        engine._model_loader.list_models.return_value = models
        assert engine.list_models() == models


class TestIsModelCached:
    def test_delegates_to_model_loader(self, engine):
        engine._model_loader = MagicMock()
        engine._model_loader.is_cached.return_value = True
        assert engine.is_model_cached("facebook/mms-tts-eng") is True
        engine._model_loader.is_cached.assert_called_once_with("facebook/mms-tts-eng")


class TestCheckDiskSpace:
    def test_delegates_to_model_loader(self, engine):
        engine._model_loader = MagicMock()
        result = DiskSpaceCheck(sufficient=True, estimated_mb=500.0, available_mb=10000.0)
        engine._model_loader.check_disk_space.return_value = result
        assert engine.check_disk_space("facebook/mms-tts-eng") == result


class TestDownloadModel:
    def test_delegates_to_model_loader(self, engine):
        engine._model_loader = MagicMock()
        cb = MagicMock()
        engine.download_model("facebook/mms-tts-eng", progress_callback=cb)
        engine._model_loader.download_model.assert_called_once_with(
            "facebook/mms-tts-eng", cb
        )

    def test_raises_on_failure(self, engine):
        engine._model_loader = MagicMock()
        engine._model_loader.download_model.side_effect = ModelLoadError("fail")
        with pytest.raises(ModelLoadError, match="fail"):
            engine.download_model("bad-model")


class TestLoadModel:
    def test_delegates_to_model_loader(self, engine):
        engine._model_loader = MagicMock()
        engine.load_model("facebook/mms-tts-eng")
        engine._model_loader.load_model.assert_called_once_with("facebook/mms-tts-eng")


class TestUnloadModel:
    def test_delegates_to_model_loader(self, engine):
        engine._model_loader = MagicMock()
        engine.unload_model()
        engine._model_loader.unload_model.assert_called_once()


# ---------------------------------------------------------------------------
# Chapter parsing
# ---------------------------------------------------------------------------

class TestParseChapters:
    def test_parses_single_chapter_from_plain_text(self, engine):
        chapters = engine.parse_chapters("Hello world.")
        assert len(chapters) == 1
        assert chapters[0].number == 1
        assert chapters[0].text == "Hello world."

    def test_parses_multiple_chapters(self, engine):
        text = "Chapter 1: Intro\nSome text.\n\nChapter 2: Middle\nMore text."
        chapters = engine.parse_chapters(text)
        assert len(chapters) == 2
        assert chapters[0].title == "Intro"
        assert chapters[1].title == "Middle"


# ---------------------------------------------------------------------------
# Synthesis
# ---------------------------------------------------------------------------

class TestSynthesize:
    @patch("local_tts.tts.engine.parse_chapters")
    @patch("local_tts.tts.engine.synthesize_chapters")
    def test_parses_then_synthesizes(
        self, mock_synth, mock_parse, engine, tmp_path
    ):
        from local_tts.tts.chapter_parser import Chapter

        chapters = [Chapter(number=1, title="Ch 1", text="Hello.")]
        mock_parse.return_value = chapters
        results = [SynthesisResult(1, "Ch 1", "chapter-01.mp3", 5.0)]
        mock_synth.return_value = results

        mock_adapter = MagicMock()
        engine._model_loader = MagicMock()
        engine._model_loader.adapter = mock_adapter

        out = engine.synthesize("Hello.", tmp_path)
        assert out == results
        mock_parse.assert_called_once_with("Hello.")
        mock_synth.assert_called_once_with(
            chapters=chapters,
            adapter=mock_adapter,
            output_dir=tmp_path,
            progress_callback=None,
        )

    def test_raises_when_no_model_loaded(self, engine, tmp_path):
        with pytest.raises(ModelLoadError, match="No model"):
            engine.synthesize("text", tmp_path)


class TestSynthesizeChapters:
    @patch("local_tts.tts.engine.synthesize_chapters")
    def test_passes_adapter_from_model_loader(self, mock_synth, engine, tmp_path):
        from local_tts.tts.chapter_parser import Chapter

        mock_adapter = MagicMock()
        engine._model_loader = MagicMock()
        engine._model_loader.adapter = mock_adapter

        chapters = [Chapter(number=1, title="Ch 1", text="Hi.")]
        mock_synth.return_value = [SynthesisResult(1, "Ch 1", "chapter-01.mp3", 2.0)]

        engine.synthesize_chapters(chapters, tmp_path)
        mock_synth.assert_called_once()
        assert mock_synth.call_args.kwargs["adapter"] is mock_adapter


# ---------------------------------------------------------------------------
# Web framework independence (REQ-MNT-modular-ai-layer)
# ---------------------------------------------------------------------------

class TestWebFrameworkIndependence:
    def test_no_fastapi_imports_in_tts_package(self):
        """The TTS subpackage must not depend on the web framework."""
        import importlib
        import pkgutil

        import local_tts.tts as tts_pkg

        tts_modules = [
            importlib.import_module(f"local_tts.tts.{info.name}")
            for info in pkgutil.iter_modules(tts_pkg.__path__)
        ]

        for mod in tts_modules:
            source_file = getattr(mod, "__file__", None)
            if source_file is None:
                continue
            content = Path(source_file).read_text()
            assert "fastapi" not in content.lower(), (
                f"{mod.__name__} imports or references FastAPI — "
                "TTS subpackage must be web-framework-independent"
            )
            assert "uvicorn" not in content.lower(), (
                f"{mod.__name__} imports or references Uvicorn — "
                "TTS subpackage must be web-framework-independent"
            )

    def test_engine_importable_without_web_framework(self):
        """TTSEngine can be imported directly without web framework context."""
        from local_tts.tts import TTSEngine

        engine = TTSEngine()
        assert engine.loaded_model_id is None
