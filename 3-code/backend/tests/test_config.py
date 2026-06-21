"""Tests for application configuration helpers.

Covers the ``_read_positive_float`` env reader and the configurable VRAM
preflight overhead factor (LOCAL_TTS_VRAM_OVERHEAD_FACTOR).
"""

from __future__ import annotations

import pytest

from local_tts import config
from local_tts.config import _read_positive_float

_VAR = "LOCAL_TTS_TEST_FLOAT"


class TestReadPositiveFloat:
    def test_returns_default_when_unset(self, monkeypatch):
        monkeypatch.delenv(_VAR, raising=False)
        assert _read_positive_float(_VAR, 1.5) == 1.5

    def test_parses_valid_float(self, monkeypatch):
        monkeypatch.setenv(_VAR, "1.1")
        assert _read_positive_float(_VAR, 1.5) == pytest.approx(1.1)

    def test_falls_back_on_unparseable(self, monkeypatch):
        monkeypatch.setenv(_VAR, "not-a-number")
        assert _read_positive_float(_VAR, 1.5) == 1.5

    def test_falls_back_on_zero(self, monkeypatch):
        monkeypatch.setenv(_VAR, "0")
        assert _read_positive_float(_VAR, 1.5) == 1.5

    def test_falls_back_on_negative(self, monkeypatch):
        monkeypatch.setenv(_VAR, "-2")
        assert _read_positive_float(_VAR, 1.5) == 1.5


class TestVramOverheadFactor:
    def test_default_constant_is_1_5(self):
        assert config.DEFAULT_VRAM_OVERHEAD_FACTOR == 1.5

    def test_factor_defaults_to_1_5_without_override(self):
        # No LOCAL_TTS_VRAM_OVERHEAD_FACTOR is set in the test environment, so
        # the resolved factor must equal the documented default — proving the
        # constant is wired through _read_positive_float with the right default.
        assert config.VRAM_OVERHEAD_FACTOR == 1.5
