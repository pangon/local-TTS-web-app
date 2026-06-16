"""Tests for two-axis preprocessing configuration resolution.

Covers: language profile resolution and default, model profile resolution and
default-subset behavior, profile registration (extensibility by config), and
the optional domain-dictionary loader's tolerance of absence/malformation.
"""

from __future__ import annotations

import pytest

from local_tts.preprocessing import profiles as pr
from local_tts.preprocessing import stages as st
from local_tts.preprocessing.profiles import (
    DEFAULT_LANGUAGE,
    DEFAULT_STAGE_ORDER,
    ModelProfile,
    default_model_profile,
    load_domain_dictionary,
    register_language_data,
    register_model_profile,
    resolve_language_profile,
    resolve_model_profile,
)
from local_tts.preprocessing.stages import (
    STAGE_LAYOUT_REPAIR,
    STAGE_UNICODE_SANITIZATION,
    StageConfig,
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


class _Stage:
    def __init__(self, name: str) -> None:
        self.name = name

    def run(self, text: str, config: StageConfig) -> str:
        return text


def _stage_class(stage_name: str) -> type:
    return type("S", (), {"name": stage_name, "run": _Stage.run})


class TestLanguageProfile:
    def test_default_language_is_italian(self):
        assert DEFAULT_LANGUAGE == "it"

    def test_none_resolves_to_default(self):
        assert resolve_language_profile(None).language == "it"
        assert resolve_language_profile("").language == "it"

    def test_explicit_language_resolves(self):
        assert resolve_language_profile("en").language == "en"

    def test_unknown_language_has_empty_data(self):
        assert resolve_language_profile("xx").data == {}

    def test_registered_data_is_returned(self):
        register_language_data("it", {"numeric": {"1": "uno"}})
        assert resolve_language_profile("it").data == {"numeric": {"1": "uno"}}

    def test_data_is_selected_per_language(self):
        register_language_data("it", {"mark": "IT"})
        register_language_data("en", {"mark": "EN"})
        assert resolve_language_profile("it").data["mark"] == "IT"
        assert resolve_language_profile("en").data["mark"] == "EN"

    def test_contributions_merge(self):
        register_language_data("it", {"numeric": {}})
        register_language_data("it", {"abbreviations": {}})
        data = resolve_language_profile("it").data
        assert set(data) == {"numeric", "abbreviations"}


class TestModelProfile:
    def test_default_stage_order_is_canonical(self):
        assert DEFAULT_STAGE_ORDER == (
            "unicode_sanitization",
            "layout_repair",
            "numeric_symbolic_verbalization",
            "abbreviation_expansion",
        )

    def test_default_profile_empty_when_no_stages_registered(self):
        assert default_model_profile().stages == ()

    def test_default_profile_is_registered_subset_in_canonical_order(self):
        # Register out of canonical order; resolution preserves canonical order.
        st.register_stage(_stage_class(STAGE_LAYOUT_REPAIR))
        st.register_stage(_stage_class(STAGE_UNICODE_SANITIZATION))
        assert default_model_profile().stages == (
            STAGE_UNICODE_SANITIZATION,
            STAGE_LAYOUT_REPAIR,
        )

    def test_unknown_model_resolves_to_default(self):
        assert resolve_model_profile("unknown/model").model_id is None

    def test_registered_model_profile_resolves(self):
        profile = ModelProfile(
            model_id="vendor/model",
            stages=(STAGE_UNICODE_SANITIZATION,),
        )
        register_model_profile(profile)
        assert resolve_model_profile("vendor/model") is profile

    def test_register_profile_without_model_id_raises(self):
        with pytest.raises(ValueError):
            register_model_profile(ModelProfile(model_id=None, stages=()))


class TestDomainDictionary:
    def test_absent_file_returns_empty(self, tmp_path):
        assert load_domain_dictionary(tmp_path / "missing.json") == {}

    def test_valid_file_loads(self, tmp_path):
        path = tmp_path / "dict.json"
        path.write_text('{"AI": "artificial intelligence"}', encoding="utf-8")
        assert load_domain_dictionary(path) == {"AI": "artificial intelligence"}

    def test_malformed_json_returns_empty(self, tmp_path):
        path = tmp_path / "dict.json"
        path.write_text("{not valid json", encoding="utf-8")
        assert load_domain_dictionary(path) == {}

    def test_non_object_json_returns_empty(self, tmp_path):
        path = tmp_path / "dict.json"
        path.write_text("[1, 2, 3]", encoding="utf-8")
        assert load_domain_dictionary(path) == {}

    def test_values_coerced_to_strings(self, tmp_path):
        path = tmp_path / "dict.json"
        path.write_text('{"n": 1}', encoding="utf-8")
        assert load_domain_dictionary(path) == {"n": "1"}
