"""Tests for ffmpeg availability validation."""

from unittest.mock import patch

import pytest

from local_tts.tts.ffmpeg_validator import FFmpegNotFoundError, validate_ffmpeg


class TestValidateFfmpeg:
    """Unit tests for the validate_ffmpeg function."""

    def test_returns_path_when_ffmpeg_found(self):
        with patch("local_tts.tts.ffmpeg_validator.shutil.which", return_value="/usr/bin/ffmpeg"):
            result = validate_ffmpeg()
            assert result == "/usr/bin/ffmpeg"

    def test_raises_when_ffmpeg_not_found(self):
        with patch("local_tts.tts.ffmpeg_validator.shutil.which", return_value=None):
            with pytest.raises(FFmpegNotFoundError, match="ffmpeg not found"):
                validate_ffmpeg()

    def test_error_message_includes_install_instructions(self):
        with patch("local_tts.tts.ffmpeg_validator.shutil.which", return_value=None):
            with pytest.raises(FFmpegNotFoundError) as exc_info:
                validate_ffmpeg()
            msg = str(exc_info.value)
            assert "sudo apt install ffmpeg" in msg
            assert "PATH" in msg
