"""Tests for the sentence-segmentation stage (REQ-F-text-layout-repair,
REQ-USA-normalized-text-review).

The stage puts each sentence on its own line so the reviewed normalized text
mirrors the synthesizer's sentence chunking. It runs last in the default
pipeline — after numeric/symbolic verbalization and abbreviation expansion — so
sentence-ending periods are not confused with thousands separators or
abbreviation dots. These tests exercise the stage in isolation (a stage is an
independently testable unit — DEC-text-preprocessing-pipeline) plus its
registration into, and ordering within, the default pipeline.
"""

from __future__ import annotations

import pytest

from local_tts.preprocessing import profiles as pr
from local_tts.preprocessing import stages as st
from local_tts.preprocessing.sentence_segmentation import (
    PARAM_SEGMENT_SENTENCES,
    SentenceSegmentationStage,
)
from local_tts.preprocessing.service import PreprocessingService
from local_tts.preprocessing.stages import (
    STAGE_ABBREVIATION_EXPANSION,
    STAGE_SENTENCE_SEGMENTATION,
    Stage,
    StageConfig,
)


@pytest.fixture(autouse=True)
def _clean_registries():
    """Snapshot/restore global registries so tests cannot leak into each other."""
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


def _stage() -> SentenceSegmentationStage:
    return SentenceSegmentationStage()


def _run(text: str, **config_kwargs) -> str:
    config = StageConfig(language="it", **config_kwargs)
    return _stage().run(text, config)


# --------------------------------------------------------------------------
# Stage contract
# --------------------------------------------------------------------------


class TestStageContract:
    def test_satisfies_stage_protocol(self):
        assert isinstance(_stage(), Stage)

    def test_declares_canonical_name(self):
        assert _stage().name == STAGE_SENTENCE_SEGMENTATION

    def test_empty_string_passthrough(self):
        assert _run("") == ""

    def test_single_sentence_unchanged(self):
        assert _run("Una sola frase.") == "Una sola frase."

    def test_text_without_terminator_unchanged(self):
        assert _run("Un titolo senza punto") == "Un titolo senza punto"


# --------------------------------------------------------------------------
# Sentence splitting
# --------------------------------------------------------------------------


class TestSentenceSplitting:
    def test_multiple_sentences_split_one_per_line(self):
        text = "Frase uno. Frase due! Frase tre?"
        assert _run(text) == "Frase uno.\nFrase due!\nFrase tre?"

    def test_blank_line_paragraph_boundary_preserved(self):
        text = "Frase uno. Frase due.\n\nAltro paragrafo. Fine."
        assert _run(text) == (
            "Frase uno.\nFrase due.\n\nAltro paragrafo.\nFine."
        )

    def test_existing_standalone_lines_preserved(self):
        # Lines already on their own (e.g. from layout repair) are untouched
        # when they hold no intra-line sentence break.
        text = "Titolo\n1\nHARI SELDON inizia qui. Continua."
        assert _run(text) == "Titolo\n1\nHARI SELDON inizia qui.\nContinua."

    def test_thousands_separator_is_not_a_sentence_break(self):
        # A dot inside a number (no following whitespace) is never a break;
        # only a terminator followed by whitespace splits.
        assert _run("Il valore 11.988 resta intero.") == (
            "Il valore 11.988 resta intero."
        )

    def test_can_be_disabled_via_param(self):
        text = "Frase uno. Frase due."
        assert (
            _run(text, params={PARAM_SEGMENT_SENTENCES: False})
            == "Frase uno. Frase due."
        )


# --------------------------------------------------------------------------
# Registration / ordering in the default pipeline
# --------------------------------------------------------------------------


class TestDefaultPipelineRegistration:
    def test_stage_registered_under_canonical_name(self):
        assert st.has_stage(STAGE_SENTENCE_SEGMENTATION)

    def test_runs_last_in_the_default_service(self):
        names = PreprocessingService().stage_names_for()
        assert names[-1] == STAGE_SENTENCE_SEGMENTATION
        # And specifically after abbreviation expansion.
        assert names.index(STAGE_SENTENCE_SEGMENTATION) > names.index(
            STAGE_ABBREVIATION_EXPANSION
        )

    def test_end_to_end_front_matter_and_body(self):
        # The reported real-world case: structural front-matter lines are not
        # glued, numbers are verbalized, and the body is segmented one sentence
        # per line (numbers/abbreviations already expanded so no mis-splits).
        raw = (
            "Parte prima\n"
            "Gli psicostorici\n"
            "1\n"
            "HARI SELDON nato nell'anno 11.988 dell'Era galattica, morto nel\n"
            "12.069. Nel calendario oggi in uso."
        )
        result = PreprocessingService().preprocess(raw).normalized_text
        lines = result.split("\n")
        assert lines[0] == "Parte prima"
        assert lines[1] == "Gli psicostorici"
        assert lines[2] == "uno"
        # The body's first sentence is intact on its own line and the
        # thousands separators were verbalized, not mis-split.
        assert lines[3].startswith("HARI SELDON nato nell'anno undicimila")
        assert lines[3].endswith(".")
        # The second body sentence is on its own line.
        assert lines[4] == "Nel calendario oggi in uso."
