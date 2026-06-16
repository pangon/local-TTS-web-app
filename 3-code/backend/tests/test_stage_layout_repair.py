"""Tests for the layout-repair stage (REQ-F-text-layout-repair).

Each acceptance criterion is exercised against the stage in isolation (a stage
is an independently testable unit — DEC-text-preprocessing-pipeline,
REQ-MNT-preprocessing-pipeline AC1), plus tests for the configurable behaviors
(de-hyphenation, reflow, page stripping, whitespace collapse), the stage's
registration into the default pipeline, and — critically — that reflow does not
defeat chapter detection (REQ-F-chapter-split-output): the repaired text is fed
to the real Chapter Parser and the chapters are still found.
"""

from __future__ import annotations

import pytest

from local_tts.preprocessing import profiles as pr
from local_tts.preprocessing import stages as st
from local_tts.preprocessing.layout_repair import (
    LayoutRepairStage,
    PARAM_COLLAPSE_WHITESPACE,
    PARAM_DEHYPHENATE,
    PARAM_REFLOW,
    PARAM_STRIP_PAGE_NUMBERS,
)
from local_tts.preprocessing.service import PreprocessingService
from local_tts.preprocessing.stages import (
    STAGE_LAYOUT_REPAIR,
    Stage,
    StageConfig,
)
from local_tts.tts.chapter_parser import parse_chapters


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


def _stage() -> LayoutRepairStage:
    return LayoutRepairStage()


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
        assert _stage().name == STAGE_LAYOUT_REPAIR

    def test_empty_string_passthrough(self):
        assert _run("") == ""

    def test_single_clean_line_unchanged(self):
        text = "Una frase pulita che non richiede riparazioni."
        assert _run(text) == text

    def test_clean_paragraphs_unchanged(self):
        text = "Primo paragrafo intero.\n\nSecondo paragrafo intero."
        assert _run(text) == text


# --------------------------------------------------------------------------
# AC: sentences broken across hard line breaks are reflowed
# --------------------------------------------------------------------------


class TestSentenceReflow:
    def test_wrapped_sentence_is_rejoined(self):
        text = "La volpe veloce\nsalta sopra il cane\npigro e dorme."
        assert _run(text) == "La volpe veloce salta sopra il cane pigro e dorme."

    def test_blank_line_separates_paragraphs_after_reflow(self):
        text = (
            "La prima frase continua\nsu due righe.\n\n"
            "La seconda frase continua\nanche lei su due righe."
        )
        assert _run(text) == (
            "La prima frase continua su due righe.\n\n"
            "La seconda frase continua anche lei su due righe."
        )

    def test_reflow_can_be_disabled(self):
        text = "riga uno\nriga due"
        assert _run(text, params={PARAM_REFLOW: False}) == "riga uno\nriga due"


# --------------------------------------------------------------------------
# AC: end-of-line hyphenation is resolved
# --------------------------------------------------------------------------


class TestDehyphenation:
    def test_hyphenated_word_is_rejoined(self):
        assert _run("exam-\nple") == "example"

    def test_dehyphenation_in_a_sentence(self):
        text = "Questo è un esem-\npio di sillaba-\nzione a fine riga."
        assert _run(text) == "Questo è un esempio di sillabazione a fine riga."

    def test_hyphen_before_digit_is_not_dehyphenated(self):
        # A numeric range "5-\n3" is not a split word: join with a space,
        # keeping the hyphen.
        assert _run("intervallo 5-\n3 unità") == "intervallo 5- 3 unità"

    def test_dehyphenation_can_be_disabled(self):
        assert _run("exam-\nple", params={PARAM_DEHYPHENATE: False}) == "exam- ple"


# --------------------------------------------------------------------------
# AC: isolated page numbers / standalone fragments are stripped
# --------------------------------------------------------------------------


class TestPageNumberStripping:
    def test_isolated_page_number_removed(self):
        text = "Fine del capitolo.\n\n42\n\nInizio del prossimo."
        assert _run(text) == "Fine del capitolo.\n\nInizio del prossimo."

    def test_decorated_page_number_removed(self):
        text = "Testo.\n\n- 12 -\n\nAltro testo."
        assert _run(text) == "Testo.\n\nAltro testo."

    def test_page_word_fragment_removed(self):
        text = "Testo.\n\nPagina 7\n\nAltro testo."
        assert _run(text) == "Testo.\n\nAltro testo."

    def test_number_within_prose_is_preserved(self):
        # A number that is part of running text is not a page-number block.
        assert _run("Ho letto 42 pagine oggi.") == "Ho letto 42 pagine oggi."

    def test_page_stripping_can_be_disabled(self):
        text = "Testo.\n\n42\n\nAltro."
        assert (
            _run(text, params={PARAM_STRIP_PAGE_NUMBERS: False})
            == "Testo.\n\n42\n\nAltro."
        )


# --------------------------------------------------------------------------
# AC: irregular whitespace is normalized
# --------------------------------------------------------------------------


class TestWhitespaceNormalization:
    def test_space_runs_collapsed(self):
        assert _run("parola      parola") == "parola parola"

    def test_tabs_collapsed_to_space(self):
        assert _run("parola\t\tparola") == "parola parola"

    def test_leading_and_trailing_spaces_trimmed(self):
        assert _run("   testo allineato   ") == "testo allineato"

    def test_runs_of_blank_lines_collapsed_to_one(self):
        text = "Primo.\n\n\n\nSecondo."
        assert _run(text) == "Primo.\n\nSecondo."

    def test_leading_and_trailing_blank_lines_removed(self):
        text = "\n\n\nSolo testo.\n\n\n"
        assert _run(text) == "Solo testo."

    def test_whitespace_collapse_can_be_disabled(self):
        # With collapse off, intra-line runs survive (lines are still split on
        # newlines and reflowed).
        assert _run("a  b", params={PARAM_COLLAPSE_WHITESPACE: False}) == "a  b"


# --------------------------------------------------------------------------
# AC: paragraph and chapter boundaries are preserved
# --------------------------------------------------------------------------


class TestBoundaryPreservation:
    def test_heading_kept_on_its_own_line_within_a_block(self):
        # Heading immediately followed by body, no blank line: the heading must
        # not be glued onto the body (protects chapter detection).
        text = "Chapter 1: The Beginning\nIl racconto comincia\nqui."
        assert _run(text) == "Chapter 1: The Beginning\nIl racconto comincia qui."

    def test_list_items_kept_on_separate_lines(self):
        text = "Spesa:\n- mele\n- pere\n- arance"
        assert _run(text) == "Spesa:\n- mele\n- pere\n- arance"

    def test_chapter_detection_survives_reflow(self):
        # Whole-document case: headings + wrapped body across blank-lined
        # paragraphs. After repair the Chapter Parser must still find both
        # chapters (REQ-F-chapter-split-output).
        raw = (
            "Chapter 1: The Start\n\n"
            "Era una notte buia\ne tempestosa. Il vento\nululava forte.\n\n"
            "12\n\n"
            "Chapter 2: The Middle\n\n"
            "Il sole sorse len-\ntamente sopra le\ncolline."
        )
        repaired = _run(raw)

        chapters = parse_chapters(repaired)
        assert len(chapters) == 2
        assert chapters[0].number == 1 and chapters[0].title == "The Start"
        assert chapters[1].number == 2 and chapters[1].title == "The Middle"
        # The body sentence was reflowed (no internal newline) and the page
        # number was stripped from chapter 1's body.
        assert "Era una notte buia e tempestosa." in chapters[0].text
        assert "12" not in chapters[0].text
        # De-hyphenation happened inside chapter 2's body.
        assert "lentamente" in chapters[1].text


# --------------------------------------------------------------------------
# Registration into the default pipeline
# --------------------------------------------------------------------------


class TestDefaultPipelineRegistration:
    def test_stage_registered_under_canonical_name(self):
        assert st.has_stage(STAGE_LAYOUT_REPAIR)

    def test_runs_after_unicode_in_the_default_service(self):
        # End-to-end through the service: the Unicode stage normalizes line
        # endings and the em dash, then layout repair reflows the wrapped
        # sentence and strips the page number.
        raw = "La frase si spezza\r\nsu righe diverse.\n\n7\n\nFine—qui."
        result = PreprocessingService().preprocess(raw)
        assert result.normalized_text == (
            "La frase si spezza su righe diverse.\n\nFine-qui."
        )
