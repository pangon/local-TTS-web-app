"""Application configuration loaded from environment variables."""

import os
from pathlib import Path


HOST: str = os.environ.get("LOCAL_TTS_HOST", "127.0.0.1")
PORT: int = int(os.environ.get("LOCAL_TTS_PORT", "8000"))

DATA_DIR: Path = Path(
    os.environ.get("LOCAL_TTS_DATA_DIR", str(Path(__file__).resolve().parents[2] / "data"))
)
