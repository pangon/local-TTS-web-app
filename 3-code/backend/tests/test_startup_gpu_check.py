"""Tests for GPU validation at startup (TASK-startup-gpu-check).

Covers REQ-F-gpu-validation acceptance criteria:
- Given the application starts, when no NVIDIA GPU with CUDA support is detected,
  then the system displays a clear error identifying the issue instead of failing silently.
- Given a compatible GPU with sufficient VRAM, then startup proceeds normally.
"""

from unittest.mock import MagicMock, patch

import pytest
from fastapi import FastAPI

from local_tts.tts.gpu_validator import GPUInfo, GPUValidationError


FAKE_GPU_INFO = GPUInfo(
    name="NVIDIA Test GPU",
    vram_total_mb=8192.0,
    vram_free_mb=7000.0,
    cuda_version="12.1",
)


async def _run_lifespan(app: FastAPI):
    """Manually trigger the ASGI lifespan startup and shutdown."""
    ctx = app.router.lifespan_context(app)
    await ctx.__aenter__()
    await ctx.__aexit__(None, None, None)


class TestStartupGpuValidationSuccess:
    """Given a compatible GPU with sufficient VRAM, startup proceeds normally."""

    @pytest.mark.anyio
    async def test_startup_succeeds_with_gpu(self):
        with (
            patch("local_tts.app.TTSEngine") as MockEngine,
            patch("local_tts.app.init_db") as mock_init_db,
        ):
            engine_instance = MagicMock()
            engine_instance.validate_gpu.return_value = FAKE_GPU_INFO
            MockEngine.return_value = engine_instance
            mock_init_db.return_value = MagicMock()

            from local_tts.app import create_app

            app = create_app()
            await _run_lifespan(app)

            engine_instance.validate_gpu.assert_called_once()

    @pytest.mark.anyio
    async def test_tts_engine_stored_on_app_state(self):
        with (
            patch("local_tts.app.TTSEngine") as MockEngine,
            patch("local_tts.app.init_db") as mock_init_db,
        ):
            engine_instance = MagicMock()
            engine_instance.validate_gpu.return_value = FAKE_GPU_INFO
            MockEngine.return_value = engine_instance
            mock_init_db.return_value = MagicMock()

            from local_tts.app import create_app

            app = create_app()
            await _run_lifespan(app)

            assert app.state.tts_engine is engine_instance

    @pytest.mark.anyio
    async def test_db_initialized_after_gpu_check(self):
        call_order = []

        with (
            patch("local_tts.app.TTSEngine") as MockEngine,
            patch("local_tts.app.init_db") as mock_init_db,
        ):
            engine_instance = MagicMock()
            engine_instance.validate_gpu.side_effect = lambda: (
                call_order.append("gpu"),
                FAKE_GPU_INFO,
            )[1]
            MockEngine.return_value = engine_instance
            mock_init_db.side_effect = lambda *a: (
                call_order.append("db"),
                MagicMock(),
            )[1]

            from local_tts.app import create_app

            app = create_app()
            await _run_lifespan(app)

            assert call_order == ["gpu", "db"]


class TestStartupGpuValidationFailure:
    """Given no NVIDIA GPU with CUDA support is detected, the system displays
    a clear error and exits instead of failing silently."""

    @pytest.mark.anyio
    async def test_startup_exits_with_clear_error_when_no_gpu(self, capsys):
        error_msg = (
            "No NVIDIA GPU with CUDA support detected. "
            "This application requires an NVIDIA GPU with CUDA drivers installed."
        )
        with (
            patch("local_tts.app.TTSEngine") as MockEngine,
            pytest.raises(SystemExit) as exc_info,
        ):
            engine_instance = MagicMock()
            engine_instance.validate_gpu.side_effect = GPUValidationError(error_msg)
            MockEngine.return_value = engine_instance

            from local_tts.app import create_app

            app = create_app()
            await _run_lifespan(app)

        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "No NVIDIA GPU" in captured.err

    @pytest.mark.anyio
    async def test_db_not_initialized_when_gpu_check_fails(self):
        with (
            patch("local_tts.app.TTSEngine") as MockEngine,
            patch("local_tts.app.init_db") as mock_init_db,
            pytest.raises(SystemExit),
        ):
            engine_instance = MagicMock()
            engine_instance.validate_gpu.side_effect = GPUValidationError("No GPU")
            MockEngine.return_value = engine_instance

            from local_tts.app import create_app

            app = create_app()
            await _run_lifespan(app)

        mock_init_db.assert_not_called()
