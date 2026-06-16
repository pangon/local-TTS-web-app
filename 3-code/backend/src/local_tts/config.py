"""Application configuration loaded from environment variables."""

import os
from pathlib import Path


HOST: str = os.environ.get("LOCAL_TTS_HOST", "127.0.0.1")
PORT: int = int(os.environ.get("LOCAL_TTS_PORT", "8000"))

DATA_DIR: Path = Path(
    os.environ.get("LOCAL_TTS_DATA_DIR", str(Path(__file__).resolve().parents[2] / "data"))
)

STATIC_DIR: Path = Path(
    os.environ.get(
        "LOCAL_TTS_STATIC_DIR",
        str(Path(__file__).resolve().parents[3] / "frontend" / "dist"),
    )
)

# Text-preprocessing configuration (DEC-text-preprocessing-pipeline). The
# optional domain dictionary is loaded from here when present; its absence
# must not break preprocessing.
PREPROCESSING_CONFIG_DIR: Path = Path(
    os.environ.get(
        "LOCAL_TTS_PREPROCESSING_CONFIG_DIR",
        str(Path(__file__).resolve().parents[2] / "config" / "preprocessing"),
    )
)

DOMAIN_DICTIONARY_PATH: Path = PREPROCESSING_CONFIG_DIR / "domain_dictionary.json"
