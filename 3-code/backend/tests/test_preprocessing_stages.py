"""Tests for the preprocessing stage abstraction and registry.

Covers: Stage protocol compliance, StageConfig defaults, and the stage
registry (register/unregister/has/get) — verifying that stages are discrete,
independently constructible units (REQ-MNT-preprocessing-pipeline AC1).
"""

from __future__ import annotations

import pytest

from local_tts.preprocessing import stages as st
from local_tts.preprocessing.stages import (
    Stage,
    StageConfig,
    get_stage,
    has_stage,
    register_stage,
    registered_stage_names,
    unregister_stage,
)


@pytest.fixture(autouse=True)
def _clean_registry():
    snapshot = dict(st._STAGE_REGISTRY)
    yield
    st._STAGE_REGISTRY.clear()
    st._STAGE_REGISTRY.update(snapshot)


class UpperStage:
    """Minimal compliant stage that uppercases its input."""

    name = "upper"

    def run(self, text: str, config: StageConfig) -> str:
        return text.upper()


class NamelessStage:
    name = ""

    def run(self, text: str, config: StageConfig) -> str:
        return text


class IncompleteStage:
    """Has a name but no run method — must not satisfy the protocol."""

    name = "incomplete"


class TestStageProtocol:
    def test_complete_stage_satisfies_protocol(self):
        assert isinstance(UpperStage(), Stage)

    def test_incomplete_stage_does_not_satisfy_protocol(self):
        assert not isinstance(IncompleteStage(), Stage)

    def test_stage_runs_independently(self):
        # A stage is exercisable in isolation given text + a config (AC1).
        result = UpperStage().run("hello", StageConfig(language="it"))
        assert result == "HELLO"


class TestStageConfig:
    def test_defaults_are_empty(self):
        cfg = StageConfig(language="it")
        assert cfg.model_id is None
        assert cfg.language_data == {}
        assert cfg.params == {}
        assert cfg.domain_dictionary == {}

    def test_is_frozen(self):
        cfg = StageConfig(language="it")
        with pytest.raises(Exception):
            cfg.language = "en"  # type: ignore[misc]


class TestStageRegistry:
    def test_has_stage_false_for_unknown(self):
        assert has_stage("nope") is False

    def test_get_unknown_stage_raises(self):
        with pytest.raises(KeyError):
            get_stage("nope")

    def test_register_and_get(self):
        register_stage(UpperStage)
        assert has_stage("upper") is True
        assert "upper" in registered_stage_names()
        stage = get_stage("upper")
        assert isinstance(stage, UpperStage)
        assert isinstance(stage, Stage)

    def test_get_returns_fresh_instance(self):
        register_stage(UpperStage)
        assert get_stage("upper") is not get_stage("upper")

    def test_register_without_name_raises(self):
        with pytest.raises(ValueError):
            register_stage(NamelessStage)

    def test_unregister(self):
        register_stage(UpperStage)
        unregister_stage("upper")
        assert has_stage("upper") is False
