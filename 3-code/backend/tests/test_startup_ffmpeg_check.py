"""Tests for ffmpeg validation at startup (TASK-startup-ffmpeg-check).

Covers REQ-F-synthesize-audiobook: ffmpeg is a system dependency required by
pydub for MP3 encoding. The application must validate its presence at startup
with a clear error message instead of failing silently during synthesis.
"""

from unittest.mock import MagicMock, patch

import pytest
from fastapi import FastAPI

from local_tts.tts.ffmpeg_validator import FFmpegNotFoundError
from local_tts.tts.gpu_validator import GPUInfo


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


def _mock_engine(*, ffmpeg_side_effect=None):
    """Create a mock TTSEngine that passes GPU validation."""
    engine = MagicMock()
    engine.validate_gpu.return_value = FAKE_GPU_INFO
    if ffmpeg_side_effect is not None:
        engine.validate_ffmpeg.side_effect = ffmpeg_side_effect
    else:
        engine.validate_ffmpeg.return_value = "/usr/bin/ffmpeg"
    return engine


class TestStartupFfmpegValidationSuccess:
    """Given ffmpeg is installed, startup proceeds normally."""

    @pytest.mark.anyio
    async def test_startup_succeeds_with_ffmpeg(self):
        with (
            patch("local_tts.app.TTSEngine") as MockEngine,
            patch("local_tts.app.init_db") as mock_init_db,
        ):
            MockEngine.return_value = _mock_engine()
            mock_init_db.return_value = MagicMock()

            from local_tts.app import create_app

            app = create_app()
            await _run_lifespan(app)

            MockEngine.return_value.validate_ffmpeg.assert_called_once()

    @pytest.mark.anyio
    async def test_ffmpeg_check_runs_after_gpu_check(self):
        call_order = []

        with (
            patch("local_tts.app.TTSEngine") as MockEngine,
            patch("local_tts.app.init_db") as mock_init_db,
        ):
            engine = _mock_engine()
            engine.validate_gpu.side_effect = lambda: (
                call_order.append("gpu"),
                FAKE_GPU_INFO,
            )[1]
            engine.validate_ffmpeg.side_effect = lambda: (
                call_order.append("ffmpeg"),
                "/usr/bin/ffmpeg",
            )[1]
            MockEngine.return_value = engine
            mock_init_db.return_value = MagicMock()

            from local_tts.app import create_app

            app = create_app()
            await _run_lifespan(app)

            assert call_order == ["gpu", "ffmpeg"]


class TestStartupFfmpegValidationFailure:
    """Given ffmpeg is not installed, the system displays a clear error and exits."""

    @pytest.mark.anyio
    async def test_startup_exits_with_clear_error_when_no_ffmpeg(self, capsys):
        error_msg = "ffmpeg not found. This application requires ffmpeg for MP3 audio encoding."
        with (
            patch("local_tts.app.TTSEngine") as MockEngine,
            pytest.raises(SystemExit) as exc_info,
        ):
            MockEngine.return_value = _mock_engine(
                ffmpeg_side_effect=FFmpegNotFoundError(error_msg),
            )

            from local_tts.app import create_app

            app = create_app()
            await _run_lifespan(app)

        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "ffmpeg not found" in captured.err

    @pytest.mark.anyio
    async def test_db_not_initialized_when_ffmpeg_check_fails(self):
        with (
            patch("local_tts.app.TTSEngine") as MockEngine,
            patch("local_tts.app.init_db") as mock_init_db,
            pytest.raises(SystemExit),
        ):
            MockEngine.return_value = _mock_engine(
                ffmpeg_side_effect=FFmpegNotFoundError("ffmpeg not found"),
            )

            from local_tts.app import create_app

            app = create_app()
            await _run_lifespan(app)

        mock_init_db.assert_not_called()
