"""Tests for the model_loader module.

Covers: listing models, cache detection, disk space checks, download with
progress callbacks, GPU loading with VRAM preflight, and unloading.
All external dependencies (huggingface_hub, transformers, torch) are mocked.
"""

from __future__ import annotations

from dataclasses import dataclass
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from local_tts.tts.gpu_validator import VRAMCheckResult
from local_tts.tts.model_loader import (
    COMPATIBLE_MODELS,
    DiskSpaceCheck,
    ModelInfo,
    ModelLoadError,
    ModelLoader,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def loader() -> ModelLoader:
    return ModelLoader()


def _make_cache_repo(repo_id: str, size_on_disk: int = 500 * 1024 * 1024):
    """Create a mock CachedRepoInfo-like object."""
    return SimpleNamespace(repo_id=repo_id, size_on_disk=size_on_disk)


def _make_scan_result(repos: list):
    return SimpleNamespace(repos=repos)


def _make_sibling(size: int):
    return SimpleNamespace(size=size)


def _make_model_info(siblings: list):
    return SimpleNamespace(siblings=siblings)


# ---------------------------------------------------------------------------
# list_models
# ---------------------------------------------------------------------------

class TestListModels:
    @patch("local_tts.tts.model_loader.scan_cache_dir")
    def test_all_models_returned(self, mock_scan, loader: ModelLoader):
        mock_scan.return_value = _make_scan_result([])
        models = loader.list_models()
        assert len(models) == len(COMPATIBLE_MODELS)
        assert all(isinstance(m, ModelInfo) for m in models)

    @patch("local_tts.tts.model_loader.scan_cache_dir")
    def test_cached_flag_set_when_in_cache(self, mock_scan, loader: ModelLoader):
        mock_scan.return_value = _make_scan_result(
            [_make_cache_repo("facebook/mms-tts-eng")]
        )
        models = loader.list_models()
        by_id = {m.model_id: m for m in models}
        assert by_id["facebook/mms-tts-eng"].is_cached is True
        assert by_id["facebook/mms-tts-ita"].is_cached is False

    @patch("local_tts.tts.model_loader.scan_cache_dir")
    def test_loaded_flag_set_for_loaded_model(self, mock_scan, loader: ModelLoader):
        mock_scan.return_value = _make_scan_result([])
        loader._loaded_model_id = "facebook/mms-tts-fra"
        models = loader.list_models()
        by_id = {m.model_id: m for m in models}
        assert by_id["facebook/mms-tts-fra"].is_loaded is True
        assert by_id["facebook/mms-tts-eng"].is_loaded is False


# ---------------------------------------------------------------------------
# is_cached
# ---------------------------------------------------------------------------

class TestIsCached:
    @patch("local_tts.tts.model_loader.scan_cache_dir")
    def test_returns_true_when_cached(self, mock_scan, loader: ModelLoader):
        mock_scan.return_value = _make_scan_result(
            [_make_cache_repo("facebook/mms-tts-eng")]
        )
        assert loader.is_cached("facebook/mms-tts-eng") is True

    @patch("local_tts.tts.model_loader.scan_cache_dir")
    def test_returns_false_when_not_cached(self, mock_scan, loader: ModelLoader):
        mock_scan.return_value = _make_scan_result([])
        assert loader.is_cached("facebook/mms-tts-eng") is False

    @patch("local_tts.tts.model_loader.scan_cache_dir")
    def test_returns_false_when_scan_fails(self, mock_scan, loader: ModelLoader):
        mock_scan.side_effect = RuntimeError("cache error")
        assert loader.is_cached("facebook/mms-tts-eng") is False


# ---------------------------------------------------------------------------
# get_model_size_mb
# ---------------------------------------------------------------------------

class TestGetModelSizeMb:
    @patch("local_tts.tts.model_loader.hf_model_info")
    def test_returns_total_size(self, mock_info, loader: ModelLoader):
        mock_info.return_value = _make_model_info(
            [_make_sibling(100 * 1024 * 1024), _make_sibling(50 * 1024 * 1024)]
        )
        assert loader.get_model_size_mb("facebook/mms-tts-eng") == 150.0

    @patch("local_tts.tts.model_loader.hf_model_info")
    def test_returns_zero_on_error(self, mock_info, loader: ModelLoader):
        mock_info.side_effect = RuntimeError("no internet")
        assert loader.get_model_size_mb("facebook/mms-tts-eng") == 0.0

    @patch("local_tts.tts.model_loader.hf_model_info")
    def test_skips_none_sizes(self, mock_info, loader: ModelLoader):
        mock_info.return_value = _make_model_info(
            [_make_sibling(100 * 1024 * 1024), _make_sibling(None)]
        )
        assert loader.get_model_size_mb("facebook/mms-tts-eng") == 100.0


# ---------------------------------------------------------------------------
# check_disk_space
# ---------------------------------------------------------------------------

class TestCheckDiskSpace:
    @patch("local_tts.tts.model_loader._get_cache_dir")
    @patch("local_tts.tts.model_loader.shutil.disk_usage")
    @patch("local_tts.tts.model_loader.hf_model_info")
    def test_sufficient_space(self, mock_info, mock_usage, mock_cache_dir, loader, tmp_path):
        mock_cache_dir.return_value = tmp_path
        mock_info.return_value = _make_model_info([_make_sibling(100 * 1024 * 1024)])
        mock_usage.return_value = SimpleNamespace(
            total=1000 * 1024 * 1024, used=500 * 1024 * 1024, free=500 * 1024 * 1024
        )
        result = loader.check_disk_space("facebook/mms-tts-eng")
        assert result.sufficient is True
        assert result.estimated_mb == 100.0
        assert result.available_mb == 500.0

    @patch("local_tts.tts.model_loader._get_cache_dir")
    @patch("local_tts.tts.model_loader.shutil.disk_usage")
    @patch("local_tts.tts.model_loader.hf_model_info")
    def test_insufficient_space(self, mock_info, mock_usage, mock_cache_dir, loader, tmp_path):
        mock_cache_dir.return_value = tmp_path
        mock_info.return_value = _make_model_info([_make_sibling(1000 * 1024 * 1024)])
        mock_usage.return_value = SimpleNamespace(
            total=1000 * 1024 * 1024, used=900 * 1024 * 1024, free=100 * 1024 * 1024
        )
        result = loader.check_disk_space("facebook/mms-tts-eng")
        assert result.sufficient is False
        assert result.estimated_mb == 1000.0
        assert result.available_mb == 100.0


# ---------------------------------------------------------------------------
# download_model
# ---------------------------------------------------------------------------

class TestDownloadModel:
    @patch("local_tts.tts.model_loader.snapshot_download")
    @patch("local_tts.tts.model_loader.scan_cache_dir")
    def test_downloads_uncached_model(self, mock_scan, mock_download, loader: ModelLoader):
        mock_scan.return_value = _make_scan_result([])
        loader.download_model("facebook/mms-tts-eng")
        mock_download.assert_called_once_with("facebook/mms-tts-eng", tqdm_class=None)

    @patch("local_tts.tts.model_loader.snapshot_download")
    @patch("local_tts.tts.model_loader.scan_cache_dir")
    def test_skips_download_when_cached(self, mock_scan, mock_download, loader: ModelLoader):
        mock_scan.return_value = _make_scan_result(
            [_make_cache_repo("facebook/mms-tts-eng")]
        )
        loader.download_model("facebook/mms-tts-eng")
        mock_download.assert_not_called()

    @patch("local_tts.tts.model_loader.snapshot_download")
    @patch("local_tts.tts.model_loader.scan_cache_dir")
    def test_calls_progress_callback_100_when_cached(self, mock_scan, mock_download, loader):
        mock_scan.return_value = _make_scan_result(
            [_make_cache_repo("facebook/mms-tts-eng")]
        )
        cb = MagicMock()
        loader.download_model("facebook/mms-tts-eng", progress_callback=cb)
        cb.assert_called_once_with(100)

    @patch("local_tts.tts.model_loader.hf_model_info")
    @patch("local_tts.tts.model_loader.snapshot_download")
    @patch("local_tts.tts.model_loader.scan_cache_dir")
    def test_passes_tqdm_class_with_callback(self, mock_scan, mock_download, mock_info, loader):
        mock_scan.return_value = _make_scan_result([])
        mock_info.return_value = _make_model_info([_make_sibling(1000)])
        cb = MagicMock()
        loader.download_model("facebook/mms-tts-eng", progress_callback=cb)
        _, kwargs = mock_download.call_args
        assert kwargs["tqdm_class"] is not None

    @patch("local_tts.tts.model_loader.snapshot_download")
    @patch("local_tts.tts.model_loader.scan_cache_dir")
    def test_raises_on_download_failure(self, mock_scan, mock_download, loader):
        mock_scan.return_value = _make_scan_result([])
        mock_download.side_effect = RuntimeError("network error")
        with pytest.raises(ModelLoadError, match="Failed to download"):
            loader.download_model("facebook/mms-tts-eng")

    @patch("local_tts.tts.model_loader.hf_model_info")
    @patch("local_tts.tts.model_loader.snapshot_download")
    @patch("local_tts.tts.model_loader.scan_cache_dir")
    def test_progress_callback_receives_100_on_success(self, mock_scan, mock_download, mock_info, loader):
        mock_scan.return_value = _make_scan_result([])
        mock_info.return_value = _make_model_info([_make_sibling(1000)])
        cb = MagicMock()
        loader.download_model("facebook/mms-tts-eng", progress_callback=cb)
        # Last call should be 100
        assert cb.call_args_list[-1][0] == (100,)


# ---------------------------------------------------------------------------
# load_model
# ---------------------------------------------------------------------------

class TestLoadModel:
    @patch("local_tts.tts.model_loader.AutoModel")
    @patch("local_tts.tts.model_loader.AutoTokenizer")
    @patch("local_tts.tts.model_loader.check_vram")
    @patch("local_tts.tts.model_loader.scan_cache_dir")
    def test_loads_cached_model(self, mock_scan, mock_vram, mock_tok, mock_model, loader):
        mock_scan.return_value = _make_scan_result(
            [_make_cache_repo("facebook/mms-tts-eng", 200 * 1024 * 1024)]
        )
        mock_vram.return_value = VRAMCheckResult(sufficient=True, required_mb=300, available_mb=8000)
        mock_pretrained = MagicMock()
        mock_model.from_pretrained.return_value = mock_pretrained
        mock_pretrained.to.return_value = mock_pretrained

        loader.load_model("facebook/mms-tts-eng")

        assert loader.loaded_model_id == "facebook/mms-tts-eng"
        mock_model.from_pretrained.assert_called_once_with("facebook/mms-tts-eng")
        mock_pretrained.to.assert_called_once_with("cuda")
        mock_tok.from_pretrained.assert_called_once_with("facebook/mms-tts-eng")

    @patch("local_tts.tts.model_loader.scan_cache_dir")
    def test_raises_when_not_cached(self, mock_scan, loader):
        mock_scan.return_value = _make_scan_result([])
        with pytest.raises(ModelLoadError, match="not cached"):
            loader.load_model("facebook/mms-tts-eng")

    @patch("local_tts.tts.model_loader.check_vram")
    @patch("local_tts.tts.model_loader.scan_cache_dir")
    def test_raises_on_insufficient_vram(self, mock_scan, mock_vram, loader):
        mock_scan.return_value = _make_scan_result(
            [_make_cache_repo("facebook/mms-tts-eng", 4000 * 1024 * 1024)]
        )
        mock_vram.return_value = VRAMCheckResult(sufficient=False, required_mb=6000, available_mb=2000)
        with pytest.raises(ModelLoadError, match="Insufficient VRAM"):
            loader.load_model("facebook/mms-tts-eng")

    @patch("local_tts.tts.model_loader.AutoModel")
    @patch("local_tts.tts.model_loader.AutoTokenizer")
    @patch("local_tts.tts.model_loader.check_vram")
    @patch("local_tts.tts.model_loader.scan_cache_dir")
    def test_skips_reload_of_same_model(self, mock_scan, mock_vram, mock_tok, mock_model, loader):
        loader._loaded_model_id = "facebook/mms-tts-eng"
        loader._model = MagicMock()
        loader._tokenizer = MagicMock()
        loader.load_model("facebook/mms-tts-eng")
        mock_model.from_pretrained.assert_not_called()

    @patch("local_tts.tts.model_loader.torch")
    @patch("local_tts.tts.model_loader.AutoModel")
    @patch("local_tts.tts.model_loader.AutoTokenizer")
    @patch("local_tts.tts.model_loader.check_vram")
    @patch("local_tts.tts.model_loader.scan_cache_dir")
    def test_unloads_previous_model_before_loading_new(
        self, mock_scan, mock_vram, mock_tok, mock_model, mock_torch, loader
    ):
        mock_torch.cuda.is_available.return_value = True
        mock_scan.return_value = _make_scan_result(
            [_make_cache_repo("facebook/mms-tts-ita", 200 * 1024 * 1024)]
        )
        mock_vram.return_value = VRAMCheckResult(sufficient=True, required_mb=300, available_mb=8000)
        mock_pretrained = MagicMock()
        mock_model.from_pretrained.return_value = mock_pretrained
        mock_pretrained.to.return_value = mock_pretrained

        loader._loaded_model_id = "facebook/mms-tts-eng"
        loader._model = MagicMock()
        loader._tokenizer = MagicMock()

        loader.load_model("facebook/mms-tts-ita")

        assert loader.loaded_model_id == "facebook/mms-tts-ita"
        mock_torch.cuda.empty_cache.assert_called_once()

    @patch("local_tts.tts.model_loader.AutoModel")
    @patch("local_tts.tts.model_loader.AutoTokenizer")
    @patch("local_tts.tts.model_loader.check_vram")
    @patch("local_tts.tts.model_loader.scan_cache_dir")
    def test_cleans_up_on_load_failure(self, mock_scan, mock_vram, mock_tok, mock_model, loader):
        mock_scan.return_value = _make_scan_result(
            [_make_cache_repo("facebook/mms-tts-eng", 200 * 1024 * 1024)]
        )
        mock_vram.return_value = VRAMCheckResult(sufficient=True, required_mb=300, available_mb=8000)
        mock_model.from_pretrained.side_effect = RuntimeError("CUDA OOM")

        with pytest.raises(ModelLoadError, match="Failed to load"):
            loader.load_model("facebook/mms-tts-eng")

        assert loader.loaded_model_id is None
        assert loader._model is None
        assert loader._tokenizer is None


# ---------------------------------------------------------------------------
# unload_model
# ---------------------------------------------------------------------------

class TestUnloadModel:
    @patch("local_tts.tts.model_loader.torch")
    def test_unloads_and_clears_cache(self, mock_torch, loader):
        mock_torch.cuda.is_available.return_value = True
        loader._loaded_model_id = "facebook/mms-tts-eng"
        loader._model = MagicMock()
        loader._tokenizer = MagicMock()

        loader.unload_model()

        assert loader._loaded_model_id is None
        assert loader._model is None
        assert loader._tokenizer is None
        mock_torch.cuda.empty_cache.assert_called_once()

    def test_noop_when_nothing_loaded(self, loader):
        loader.unload_model()
        assert loader._loaded_model_id is None


# ---------------------------------------------------------------------------
# Properties
# ---------------------------------------------------------------------------

class TestProperties:
    def test_model_raises_when_none(self, loader):
        with pytest.raises(ModelLoadError, match="No model"):
            _ = loader.model

    def test_tokenizer_raises_when_none(self, loader):
        with pytest.raises(ModelLoadError, match="No model"):
            _ = loader.tokenizer

    def test_loaded_model_id_defaults_none(self, loader):
        assert loader.loaded_model_id is None


# ---------------------------------------------------------------------------
# Progress tqdm wrapper
# ---------------------------------------------------------------------------

class TestProgressTqdm:
    @patch("local_tts.tts.model_loader.hf_model_info")
    def test_tqdm_wrapper_calls_callback(self, mock_info):
        from local_tts.tts.model_loader import _make_progress_tqdm

        mock_info.return_value = _make_model_info([_make_sibling(1000)])
        cb = MagicMock()

        tqdm_cls = _make_progress_tqdm("test-model", cb)
        instance = tqdm_cls(total=500)
        instance.update(500)  # 50% of total 1000
        instance.update(500)  # 100% of total 1000

        percentages = [call[0][0] for call in cb.call_args_list]
        assert 50 in percentages
        assert 99 in percentages  # capped at 99, final 100 sent by download_model

    @patch("local_tts.tts.model_loader.hf_model_info")
    def test_tqdm_wrapper_handles_unknown_size(self, mock_info):
        from local_tts.tts.model_loader import _make_progress_tqdm

        mock_info.side_effect = RuntimeError("no info")
        cb = MagicMock()

        tqdm_cls = _make_progress_tqdm("test-model", cb)
        instance = tqdm_cls(total=1000)
        instance.update(500)

        cb.assert_not_called()  # Can't compute percentage without total size

    @patch("local_tts.tts.model_loader.hf_model_info")
    def test_tqdm_wrapper_supports_context_manager(self, mock_info):
        from local_tts.tts.model_loader import _make_progress_tqdm

        mock_info.return_value = _make_model_info([_make_sibling(1000)])
        cb = MagicMock()

        tqdm_cls = _make_progress_tqdm("test-model", cb)
        with tqdm_cls(total=1000) as bar:
            bar.update(100)
