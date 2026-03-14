"""Application configuration loaded from environment variables."""

import os


HOST: str = os.environ.get("LOCAL_TTS_HOST", "127.0.0.1")
PORT: int = int(os.environ.get("LOCAL_TTS_PORT", "8000"))
