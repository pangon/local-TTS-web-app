"""Tests for the model adapter abstraction.

Covers: ModelAdapter protocol definition, adapter registry (get_adapter,
has_adapter), and runtime protocol checking.
"""

from __future__ import annotations

from typing import Any

import numpy as np
import pytest

from local_tts.tts.adapters import (
    ModelAdapter,
    _ADAPTER_REGISTRY,
    get_adapter,
    has_adapter,
)


# ---------------------------------------------------------------------------
# Concrete test adapter
# ---------------------------------------------------------------------------

class FakeAdapter:
    """Minimal adapter implementation for testing."""

    def __init__(self) -> None:
        self._loaded = False

    def load(self, model_id: str, device: str) -> None:
        self._loaded = True

    def synthesize(self, text: str, **kwargs: Any) -> np.ndarray:
        return np.zeros(16000, dtype=np.float32)

    @property
    def sample_rate(self) -> int:
        return 16000

    def unload(self) -> None:
        self._loaded = False


class IncompleteAdapter:
    """Adapter missing required methods — should not satisfy the protocol."""

    def load(self, model_id: str, device: str) -> None: ...


# ---------------------------------------------------------------------------
# Protocol compliance
# ---------------------------------------------------------------------------

class TestModelAdapterProtocol:
    def test_complete_adapter_satisfies_protocol(self):
        adapter = FakeAdapter()
        assert isinstance(adapter, ModelAdapter)

    def test_incomplete_adapter_does_not_satisfy_protocol(self):
        adapter = IncompleteAdapter()
        assert not isinstance(adapter, ModelAdapter)


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

class TestAdapterRegistry:
    def test_has_adapter_returns_false_for_unknown(self):
        assert has_adapter("nonexistent/model") is False

    def test_get_adapter_returns_none_for_unknown(self):
        assert get_adapter("nonexistent/model") is None

    def test_registered_adapter_is_found(self):
        _ADAPTER_REGISTRY["test/fake-model"] = FakeAdapter
        try:
            assert has_adapter("test/fake-model") is True
            adapter = get_adapter("test/fake-model")
            assert adapter is not None
            assert isinstance(adapter, ModelAdapter)
            assert isinstance(adapter, FakeAdapter)
        finally:
            del _ADAPTER_REGISTRY["test/fake-model"]

    def test_get_adapter_creates_new_instance(self):
        _ADAPTER_REGISTRY["test/fake-model"] = FakeAdapter
        try:
            a1 = get_adapter("test/fake-model")
            a2 = get_adapter("test/fake-model")
            assert a1 is not a2
        finally:
            del _ADAPTER_REGISTRY["test/fake-model"]

    def test_registry_contains_implemented_adapters(self):
        # Registry should contain entries for all implemented adapters.
        # At minimum, the Kokoro adapter is registered.
        assert "hexgrad/Kokoro-82M" in _ADAPTER_REGISTRY
