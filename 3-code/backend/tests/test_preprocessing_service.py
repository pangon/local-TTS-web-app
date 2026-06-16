"""End-to-end tests for the Preprocessing Service.

These exercise REQ-MNT-preprocessing-pipeline's acceptance criteria through
the orchestrator:

- AC1: discrete stages run as an ordered pipeline.
- AC2: a configured output language selects language-appropriate behavior.
- AC3: two different models apply model-specific configuration without
  changing shared stage implementations.
- AC4: a new language/model is introduced by registration alone.

It also verifies char-count metadata, default language, model_id passthrough,
and that the optional domain dictionary reaches stages.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from local_tts.preprocessing import profiles as pr
from local_tts.preprocessing import stages as st
from local_tts.preprocessing.profiles import (
    ModelProfile,
    register_language_data,
    register_model_profile,
)
from local_tts.preprocessing.service import PreprocessingService, PreprocessResult
from local_tts.preprocessing.stages import (
    STAGE_LAYOUT_REPAIR,
    STAGE_UNICODE_SANITIZATION,
    StageConfig,
    register_stage,
)


@pytest.fixture(autouse=True)
def _clean_registries():
    stage_snap = dict(st._STAGE_REGISTRY)
    lang_snap = {k: dict(v) for k, v in pr._LANGUAGE_DATA.items()}
    model_snap = dict(pr._MODEL_PROFILES)
    yield
    st._STAGE_REGISTRY.clear()
    st._STAGE_REGISTRY.update(stage_snap)
    pr._LANGUAGE_DATA.clear()
    pr._LANGUAGE_DATA.update(lang_snap)
    pr._MODEL_PROFILES.clear()
    pr._MODEL_PROFILES.update(model_snap)


def _service() -> PreprocessingService:
    # Force an empty domain dictionary regardless of any on-disk file.
    return PreprocessingService(domain_dictionary_path=Path("/nonexistent.json"))


# --- Stages used across tests (registered under canonical names so they join
#     the default model profile automatically). ------------------------------


class UnicodeMarker:
    """Stands in for the unicode stage; appends a marker + optional param."""

    name = STAGE_UNICODE_SANITIZATION

    def run(self, text: str, config: StageConfig) -> str:
        return text + "U" + str(config.params.get("extra", ""))


class LayoutMarker:
    name = STAGE_LAYOUT_REPAIR

    def run(self, text: str, config: StageConfig) -> str:
        return text + "L"


class TestIdentityAndMetadata:
    def test_identity_when_no_stages_registered(self):
        result = _service().preprocess("hello world")
        assert isinstance(result, PreprocessResult)
        assert result.normalized_text == "hello world"

    def test_default_language_and_model_passthrough(self):
        result = _service().preprocess("x", model_id="vendor/model")
        assert result.language == "it"
        assert result.model_id == "vendor/model"

    def test_explicit_language_recorded(self):
        assert _service().preprocess("x", language="en").language == "en"

    def test_char_counts(self):
        class Doubler:
            name = STAGE_UNICODE_SANITIZATION

            def run(self, text: str, config: StageConfig) -> str:
                return text * 2

        register_stage(Doubler)
        result = _service().preprocess("abcd")
        assert result.original_char_count == 4
        assert result.normalized_char_count == 8


class TestPipelineOrdering:
    def test_stages_run_in_canonical_order(self):
        # unicode runs before layout: "hi" -> "hiU" -> "hiUL".
        register_stage(UnicodeMarker)
        register_stage(LayoutMarker)
        assert _service().preprocess("hi").normalized_text == "hiUL"

    def test_stage_names_for_reflects_registered_subset(self):
        register_stage(LayoutMarker)
        register_stage(UnicodeMarker)
        # Canonical order preserved regardless of registration order (AC4).
        assert _service().stage_names_for() == [
            STAGE_UNICODE_SANITIZATION,
            STAGE_LAYOUT_REPAIR,
        ]


class TestLanguageSelection:
    """AC2: language-appropriate behavior is selected by output language."""

    def test_language_data_drives_behavior(self):
        class LangStage:
            name = STAGE_UNICODE_SANITIZATION

            def run(self, text: str, config: StageConfig) -> str:
                return text + config.language_data.get("mark", "")

        register_stage(LangStage)
        register_language_data("it", {"mark": "·it"})
        register_language_data("en", {"mark": "·en"})

        svc = _service()
        assert svc.preprocess("x", language="it").normalized_text == "x·it"
        assert svc.preprocess("x", language="en").normalized_text == "x·en"
        # Default (None) uses Italian.
        assert svc.preprocess("x").normalized_text == "x·it"


class TestModelProfileSelection:
    """AC3: per-model config without changing shared stage code."""

    def test_model_profile_changes_active_stages_and_params(self):
        register_stage(UnicodeMarker)
        register_stage(LayoutMarker)
        # Custom profile: only the unicode stage runs, with an extra param.
        register_model_profile(
            ModelProfile(
                model_id="vendor/model",
                stages=(STAGE_UNICODE_SANITIZATION,),
                stage_params={STAGE_UNICODE_SANITIZATION: {"extra": "!"}},
            )
        )
        svc = _service()

        # Default model runs both stages, no extra param.
        assert svc.preprocess("").normalized_text == "UL"
        # Custom model runs only unicode, with the extra param — same classes.
        assert svc.preprocess("", model_id="vendor/model").normalized_text == "U!"


class TestDomainDictionary:
    def test_absent_dictionary_is_empty(self):
        assert _service().domain_dictionary == {}

    def test_dictionary_reaches_stage(self, tmp_path):
        path = tmp_path / "domain.json"
        path.write_text('{"AI": "intelligenza artificiale"}', encoding="utf-8")

        class DictStage:
            name = STAGE_UNICODE_SANITIZATION

            def run(self, text: str, config: StageConfig) -> str:
                return text + "|" + config.domain_dictionary.get("AI", "")

        register_stage(DictStage)
        svc = PreprocessingService(domain_dictionary_path=path)
        assert (
            svc.preprocess("x").normalized_text == "x|intelligenza artificiale"
        )
