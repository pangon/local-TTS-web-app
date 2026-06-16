"""Tests for the preprocessing pipeline runner.

Covers: ordered stage execution, identity for an empty pipeline, and
build_pipeline's strict resolution of model-profile stage names.
"""

from __future__ import annotations

import pytest

from local_tts.preprocessing import stages as st
from local_tts.preprocessing.pipeline import Pipeline, build_pipeline
from local_tts.preprocessing.profiles import ModelProfile
from local_tts.preprocessing.stages import StageConfig


@pytest.fixture(autouse=True)
def _clean_registry():
    snapshot = dict(st._STAGE_REGISTRY)
    yield
    st._STAGE_REGISTRY.clear()
    st._STAGE_REGISTRY.update(snapshot)


class AppendStage:
    def __init__(self, name: str, token: str) -> None:
        self.name = name
        self._token = token

    def run(self, text: str, config: StageConfig) -> str:
        return text + self._token


def _config_for(_stage):
    return StageConfig(language="it")


class TestPipeline:
    def test_runs_stages_in_order(self):
        pipeline = Pipeline([AppendStage("a", "A"), AppendStage("b", "B")])
        assert pipeline.run("x", _config_for) == "xAB"

    def test_empty_pipeline_is_identity(self):
        assert Pipeline([]).run("unchanged", _config_for) == "unchanged"

    def test_stage_names_exposed(self):
        pipeline = Pipeline([AppendStage("a", "A"), AppendStage("b", "B")])
        assert pipeline.stage_names == ["a", "b"]

    def test_config_resolved_per_stage(self):
        seen: list[str] = []

        class Recorder:
            name = "rec"

            def run(self, text: str, config: StageConfig) -> str:
                seen.append(config.language)
                return text

        Pipeline([Recorder()]).run("x", lambda s: StageConfig(language="en"))
        assert seen == ["en"]


class StageOne:
    name = "s1"

    def run(self, text: str, config: StageConfig) -> str:
        return text + "1"


class StageTwo:
    name = "s2"

    def run(self, text: str, config: StageConfig) -> str:
        return text + "2"


class TestBuildPipeline:
    def test_builds_stages_in_profile_order(self):
        st.register_stage(StageOne)
        st.register_stage(StageTwo)
        profile = ModelProfile(model_id=None, stages=("s2", "s1"))
        pipeline = build_pipeline(profile)
        assert pipeline.stage_names == ["s2", "s1"]
        assert pipeline.run("x", _config_for) == "x21"

    def test_unregistered_stage_name_raises(self):
        profile = ModelProfile(model_id=None, stages=("never_registered",))
        with pytest.raises(KeyError):
            build_pipeline(profile)
