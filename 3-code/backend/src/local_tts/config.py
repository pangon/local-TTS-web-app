"""Application configuration loaded from environment variables."""

import os
from pathlib import Path


def _read_positive_float(var_name: str, default: float) -> float:
    """Read a strictly-positive float from the environment, else *default*.

    An unset, unparseable, or non-positive value falls back to *default*, so a
    malformed override can never disable or invert the guard it tunes.
    """
    raw = os.environ.get(var_name)
    if raw is None:
        return default
    try:
        value = float(raw)
    except ValueError:
        return default
    return value if value > 0 else default


HOST: str = os.environ.get("LOCAL_TTS_HOST", "127.0.0.1")
PORT: int = int(os.environ.get("LOCAL_TTS_PORT", "8000"))

# VRAM preflight safety margin (REQ-F-gpu-validation): before loading, a model's
# estimated VRAM need is its on-disk size times this factor, checked against free
# VRAM. Default 1.5; override via LOCAL_TTS_VRAM_OVERHEAD_FACTOR to tune the guard
# — e.g. lower it to load a model that is borderline on a smaller GPU. The lower
# the value, the higher the risk of a runtime out-of-memory during synthesis.
DEFAULT_VRAM_OVERHEAD_FACTOR: float = 1.5
VRAM_OVERHEAD_FACTOR: float = _read_positive_float(
    "LOCAL_TTS_VRAM_OVERHEAD_FACTOR", DEFAULT_VRAM_OVERHEAD_FACTOR
)

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
