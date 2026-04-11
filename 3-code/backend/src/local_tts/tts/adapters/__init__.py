"""Model adapter abstraction for heterogeneous TTS models.

Each TTS model requires its own loading and inference procedure.
The ``ModelAdapter`` protocol defines the common interface that all
model-specific adapters must implement.  The adapter registry maps
HuggingFace model IDs to their concrete adapter classes.

New adapters are registered by importing them here and adding an entry
to ``_ADAPTER_REGISTRY``.
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

import numpy as np


@runtime_checkable
class ModelAdapter(Protocol):
    """Common interface for model-specific loading and inference.

    Each concrete adapter encapsulates the library-specific details of
    loading a TTS model onto a device, running inference, and releasing
    GPU memory.
    """

    def load(self, model_id: str, device: str) -> None:
        """Load model and any required tokenizer/processor onto *device*.

        Args:
            model_id: HuggingFace model ID (e.g. ``"hexgrad/Kokoro-82M"``).
            device: PyTorch device string (e.g. ``"cuda"``).
        """
        ...

    def synthesize(self, text: str, **kwargs: Any) -> np.ndarray:
        """Run TTS inference and return raw audio samples.

        Args:
            text: Input text to synthesize.
            **kwargs: Model-specific options (voice, language, etc.).

        Returns:
            1-D float32 numpy array of audio samples.
        """
        ...

    @property
    def sample_rate(self) -> int:
        """The output sample rate of the loaded model in Hz."""
        ...

    def unload(self) -> None:
        """Release GPU memory and any held resources."""
        ...


# ---------------------------------------------------------------------------
# Adapter registry
# ---------------------------------------------------------------------------

# Maps HuggingFace model ID -> concrete adapter class.
# Each TASK-loader-* task adds its adapter here upon implementation.
_ADAPTER_REGISTRY: dict[str, type[ModelAdapter]] = {
    # "hexgrad/Kokoro-82M": KokoroAdapter,         # TASK-loader-kokoro
    # "ResembleAI/chatterbox": ChatterboxAdapter,   # TASK-loader-chatterbox
    # "coqui/XTTS-v2": XTTSv2Adapter,              # TASK-loader-xtts-v2
    # ... (added by adapter implementation tasks)
}


def get_adapter(model_id: str) -> ModelAdapter | None:
    """Create a new adapter instance for *model_id*, or return ``None``."""
    adapter_cls = _ADAPTER_REGISTRY.get(model_id)
    if adapter_cls is None:
        return None
    return adapter_cls()


def has_adapter(model_id: str) -> bool:
    """Check whether a concrete adapter is registered for *model_id*."""
    return model_id in _ADAPTER_REGISTRY
