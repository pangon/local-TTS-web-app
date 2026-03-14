"""ffmpeg availability validation.

Checks that ffmpeg is installed and executable on the system. This is required
by pydub for MP3 encoding during synthesis (REQ-F-synthesize-audiobook).
"""

from __future__ import annotations

import shutil


class FFmpegNotFoundError(Exception):
    """Raised when ffmpeg is not found on the system."""


def validate_ffmpeg() -> str:
    """Verify that ffmpeg is available on the system PATH.

    Returns:
        The absolute path to the ffmpeg executable.

    Raises:
        FFmpegNotFoundError: If ffmpeg is not found.
    """
    ffmpeg_path = shutil.which("ffmpeg")
    if ffmpeg_path is None:
        raise FFmpegNotFoundError(
            "ffmpeg not found. This application requires ffmpeg for MP3 audio encoding. "
            "Please install ffmpeg and ensure it is on your system PATH.\n"
            "  - Linux (Debian/Ubuntu): sudo apt install ffmpeg\n"
            "  - Linux (Fedora): sudo dnf install ffmpeg\n"
            "  - Windows: download from https://ffmpeg.org/download.html and add to PATH"
        )
    return ffmpeg_path
