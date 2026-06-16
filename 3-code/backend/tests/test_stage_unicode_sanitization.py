"""Tests for the Unicode sanitization stage (REQ-F-text-unicode-sanitization).

Each acceptance criterion is exercised against the stage in isolation (a stage
is an independently testable unit — DEC-text-preprocessing-pipeline,
REQ-MNT-preprocessing-pipeline AC1), plus tests for the configurable behaviors
(emoji mode, dash form, normalization form), the language-data seam, and the
stage's registration into the default pipeline.

Non-printable and ambiguous characters are written as explicit ``\\u``/``\\U``
escapes so the fixtures stay readable and unambiguous.
"""

from __future__ import annotations

import pytest

from local_tts.preprocessing import profiles as pr
from local_tts.preprocessing import stages as st
from local_tts.preprocessing.service import PreprocessingService
from local_tts.preprocessing.stages import (
    STAGE_UNICODE_SANITIZATION,
    Stage,
    StageConfig,
)
from local_tts.preprocessing.unicode_sanitization import (
    EMOJI_MODE_VERBALIZE,
    EMOJI_NAMES_KEY,
    LANGUAGE_DATA_NAMESPACE,
    PARAM_DASH_REPLACEMENT,
    PARAM_EMOJI_MODE,
    PARAM_UNICODE_FORM,
    UnicodeSanitizationStage,
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


def _stage() -> UnicodeSanitizationStage:
    return UnicodeSanitizationStage()


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
        assert _stage().name == STAGE_UNICODE_SANITIZATION

    def test_runs_independently_with_minimal_config(self):
        assert _run("ciao") == "ciao"

    def test_empty_string_passthrough(self):
        assert _run("") == ""

    def test_clean_text_is_unchanged(self):
        text = "Il numero 3, la parola 'casa' e la frase: ecco qua."
        assert _run(text) == text


# --------------------------------------------------------------------------
# AC: invisible / zero-width / control characters are removed
# --------------------------------------------------------------------------


class TestInvisibleAndControlRemoval:
    def test_zero_width_space_removed(self):
        assert _run("a​b") == "ab"

    def test_zero_width_joiner_and_non_joiner_removed(self):
        assert _run("a‌b‍c") == "abc"

    def test_soft_hyphen_removed(self):
        assert _run("co­sa") == "cosa"

    def test_bom_removed(self):
        assert _run("﻿Testo") == "Testo"

    def test_word_joiner_and_bidi_marks_removed(self):
        assert _run("a⁠b‎‏c") == "abc"

    def test_control_characters_removed(self):
        assert _run("a\x07b\x00c\x1fd") == "abcd"

    def test_del_and_c1_controls_removed(self):
        assert _run("a\x7fb\x9fc") == "abc"

    def test_private_use_character_removed(self):
        # U+E000 is in the BMP Private Use Area (category Co): disallowed.
        assert _run("ab") == "ab"

    def test_newline_is_preserved(self):
        # Paragraph/chapter boundaries must survive for layout repair.
        assert _run("riga uno\nriga due") == "riga uno\nriga due"

    def test_blank_line_between_paragraphs_preserved(self):
        assert _run("par uno\n\npar due") == "par uno\n\npar due"


# --------------------------------------------------------------------------
# AC: non-breaking spaces and whitespace variants become normal spaces
# --------------------------------------------------------------------------


class TestWhitespaceVariants:
    def test_nbsp_becomes_space(self):
        assert _run("a b") == "a b"

    def test_narrow_nbsp_becomes_space(self):
        assert _run("a b") == "a b"

    @pytest.mark.parametrize(
        "ws",
        [
            " ",  # no-break space
            " ",  # en space
            " ",  # em space
            " ",  # thin space
            " ",  # medium mathematical space
            "　",  # ideographic space
            " ",  # ogham space mark
        ],
    )
    def test_unicode_space_separators_become_space(self, ws):
        assert _run(f"a{ws}b") == "a b"

    def test_tab_becomes_space(self):
        assert _run("a\tb") == "a b"

    def test_runs_are_not_collapsed(self):
        # Collapsing runs is the layout-repair stage's job, not this one.
        assert _run("a  b") == "a  b"


# --------------------------------------------------------------------------
# AC: dash variants normalized to a consistent form
# --------------------------------------------------------------------------


class TestDashNormalization:
    def test_em_en_figure_dashes_normalized_to_hyphen(self):
        # em dash, en dash, figure dash
        assert _run("a—b–c‒d") == "a-b-c-d"

    def test_minus_sign_and_horizontal_bar_normalized(self):
        # minus sign (U+2212), horizontal bar (U+2015)
        assert _run("5−3 ― fine") == "5-3 - fine"

    def test_ascii_hyphen_unchanged(self):
        assert _run("ben-essere") == "ben-essere"

    def test_dash_replacement_is_configurable(self):
        result = _run(
            "parola—parola", params={PARAM_DASH_REPLACEMENT: " - "}
        )
        assert result == "parola - parola"


# --------------------------------------------------------------------------
# AC: smart / typographic quotes normalized to standard equivalents
# --------------------------------------------------------------------------


class TestQuoteNormalization:
    def test_smart_double_quotes_normalized(self):
        assert _run("“ciao”") == '"ciao"'

    def test_smart_single_quotes_and_apostrophe_normalized(self):
        assert _run("‘ciao’ e l’auto") == "'ciao' e l'auto"

    def test_guillemets_normalized_to_double_quotes(self):
        assert _run("«citazione»") == '"citazione"'

    def test_primes_normalized(self):
        assert _run("5′ 6″") == "5' 6\""


# --------------------------------------------------------------------------
# AC: emoji removed or verbalized per configuration
# --------------------------------------------------------------------------


class TestEmojiHandling:
    def test_emoji_removed_by_default(self):
        result = _run("Buongiorno \U0001F600 a tutti")
        assert "\U0001F600" not in result
        assert "Buongiorno" in result and "a tutti" in result

    def test_heart_and_symbol_emoji_removed(self):
        # heavy black heart (U+2764), fire (U+1F525)
        result = _run("amore ❤ e fuoco \U0001F525")
        assert "❤" not in result and "\U0001F525" not in result

    def test_zwj_emoji_sequence_fully_removed(self):
        # man + ZWJ + woman + ZWJ + girl
        family = "\U0001F468‍\U0001F469‍\U0001F467"
        result = _run(f"famiglia {family} qui")
        for cp in ("\U0001F468", "\U0001F469", "\U0001F467", "‍"):
            assert cp not in result

    def test_emoji_verbalized_from_language_table(self):
        result = _run(
            "ciao \U0001F600",
            params={PARAM_EMOJI_MODE: EMOJI_MODE_VERBALIZE},
            language_data={
                LANGUAGE_DATA_NAMESPACE: {
                    EMOJI_NAMES_KEY: {"\U0001F600": "faccina sorridente"}
                }
            },
        )
        assert "faccina sorridente" in result
        assert "\U0001F600" not in result

    def test_emoji_verbalized_falls_back_to_unicode_name(self):
        # U+1F680 ROCKET, absent from any supplied table.
        result = _run(
            "vai \U0001F680",
            params={PARAM_EMOJI_MODE: EMOJI_MODE_VERBALIZE},
        )
        assert "rocket" in result
        assert "\U0001F680" not in result

    def test_unknown_emoji_mode_falls_back_to_removal(self):
        result = _run("ciao \U0001F600", params={PARAM_EMOJI_MODE: "weird"})
        assert "\U0001F600" not in result

    def test_non_emoji_symbols_are_preserved(self):
        # Copyright/registered/trademark are not emoji and must survive
        # (the verbalization stage handles symbols, not this one).
        text = "Marchio © ® ™ ok"
        assert _run(text) == text


# --------------------------------------------------------------------------
# Line-ending and Unicode-form normalization
# --------------------------------------------------------------------------


class TestLineEndingsAndForm:
    def test_crlf_normalized_to_lf(self):
        assert _run("a\r\nb") == "a\nb"

    def test_lone_cr_normalized_to_lf(self):
        assert _run("a\rb") == "a\nb"

    def test_form_feed_and_vertical_tab_normalized_to_lf(self):
        assert _run("a\x0cb\x0bc") == "a\nb\nc"

    def test_line_and_paragraph_separators_normalized_to_lf(self):
        # U+2028 line separator, U+2029 paragraph separator
        assert _run("a b c") == "a\nb\nc"

    def test_decomposed_accents_composed_by_default_nfc(self):
        # "e" + combining acute (U+0301) -> precomposed "é" (U+00E9).
        assert _run("perché") == "perché"

    def test_normalization_form_can_be_disabled(self):
        # With form disabled the combining mark (category Mn) is preserved.
        result = _run("é", params={PARAM_UNICODE_FORM: "none"})
        assert result == "é"

    def test_nfkc_form_expands_compatibility_characters(self):
        # Fullwidth digit one (U+FF11) -> ASCII "1" under NFKC.
        assert _run("１", params={PARAM_UNICODE_FORM: "NFKC"}) == "1"


# --------------------------------------------------------------------------
# Registration into the default pipeline
# --------------------------------------------------------------------------


class TestDefaultPipelineRegistration:
    def test_stage_registered_under_canonical_name(self):
        assert st.has_stage(STAGE_UNICODE_SANITIZATION)

    def test_runs_as_part_of_the_service(self):
        # The service builds the default pipeline, which now includes this
        # stage: smart quotes are normalized end-to-end.
        result = PreprocessingService().preprocess("“ciao” amico")
        assert result.normalized_text == '"ciao" amico'

    def test_builtin_italian_emoji_table_is_registered(self):
        profile = pr.resolve_language_profile("it")
        table = profile.data.get(LANGUAGE_DATA_NAMESPACE, {}).get(
            EMOJI_NAMES_KEY, {}
        )
        assert table.get("\U0001F600") == "faccina sorridente"
