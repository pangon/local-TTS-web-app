"""Tests for the abbreviation-expansion stage.

Exercises every acceptance criterion of REQ-F-abbreviation-expansion against the
stage in isolation (a stage is an independently testable unit —
DEC-text-preprocessing-pipeline, REQ-MNT-preprocessing-pipeline AC1): common
abbreviations read as their full spoken word, Italian-convention expansions
(DEC-default-italian-language), an optional domain dictionary applied when
supplied, and built-in expansion that still works when no dictionary is given.
Also covers the configurable per-concern switches, case sensitivity, graceful
no-op without language data, whole-token matching, sentence-period handling, and
registration into the default pipeline.
"""

from __future__ import annotations

import pytest

from local_tts.preprocessing import profiles as pr
from local_tts.preprocessing import stages as st
from local_tts.preprocessing.abbreviation_expansion import (
    ABBREVIATIONS_KEY,
    AbbreviationExpansionStage,
    BUILTIN_LANGUAGE_DATA,
    LANGUAGE_DATA_NAMESPACE,
    PARAM_ABBREVIATION_CASE_INSENSITIVE,
    PARAM_APPLY_DOMAIN_DICTIONARY,
    PARAM_DOMAIN_CASE_INSENSITIVE,
    PARAM_EXPAND_ABBREVIATIONS,
)
from local_tts.preprocessing.service import PreprocessingService
from local_tts.preprocessing.stages import (
    STAGE_ABBREVIATION_EXPANSION,
    Stage,
    StageConfig,
)

IT_DATA = BUILTIN_LANGUAGE_DATA["it"]


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


def _stage() -> AbbreviationExpansionStage:
    return AbbreviationExpansionStage()


def _run(text: str, language_data=IT_DATA, **config_kwargs) -> str:
    config = StageConfig(language="it", language_data=language_data, **config_kwargs)
    return _stage().run(text, config)


# --------------------------------------------------------------------------
# Stage contract
# --------------------------------------------------------------------------


class TestStageContract:
    def test_satisfies_stage_protocol(self):
        assert isinstance(_stage(), Stage)

    def test_declares_canonical_name(self):
        assert _stage().name == STAGE_ABBREVIATION_EXPANSION

    def test_empty_string_passthrough(self):
        assert _run("") == ""

    def test_text_without_abbreviations_unchanged(self):
        text = "Questa frase non contiene nulla da espandere."
        assert _run(text) == text


# --------------------------------------------------------------------------
# AC1: a common abbreviation is read as its full spoken word
# --------------------------------------------------------------------------


class TestCommonAbbreviations:
    def test_ecc_expands(self):
        # End of text: the abbreviation period also closes the sentence.
        assert _run("Mele, pere, ecc.") == "Mele, pere, eccetera."

    def test_etc_expands(self):
        assert _run("Mele, pere, etc.") == "Mele, pere, eccetera."

    def test_ecc_midsentence_keeps_no_extra_period(self):
        # Followed by lowercase continuation: just the spoken word, no period.
        assert _run("Mele, ecc. e altro") == "Mele, eccetera e altro"

    def test_eg_expands_to_italian_form(self):
        assert _run("Frutta, e.g. mele.") == "Frutta, per esempio mele."

    def test_ie_expands(self):
        assert _run("Subito, i.e. ora.") == "Subito, cioè ora."

    def test_es_expands(self):
        assert _run("Vedi es. sopra.") == "Vedi esempio sopra."

    def test_ex_expands(self):
        assert _run("Vedi ex. sopra.") == "Vedi esempio sopra."


# --------------------------------------------------------------------------
# AC2: Italian common abbreviations verbalized following Italian conventions
# --------------------------------------------------------------------------


class TestItalianConventions:
    def test_honorific_before_name_drops_period(self):
        # The period after a title is an abbreviation marker, not a sentence
        # end: it must not survive even before a capitalized proper name.
        assert _run("Il sig. Rossi è qui.") == "Il signor Rossi è qui."

    def test_dottoressa_longer_match_wins_over_dott(self):
        assert _run("La dott.ssa Bianchi.") == "La dottoressa Bianchi."

    def test_professor(self):
        assert _run("Il prof. Verdi insegna.") == "Il professor Verdi insegna."

    def test_page_reference(self):
        assert _run("Vedi pag. dieci.") == "Vedi pagina dieci."

    def test_multipart_per_esempio(self):
        # Longest-first: "p.es." wins over the "es." it contains.
        assert _run("Lavoro, p.es. di notte.") == "Lavoro, per esempio di notte."

    def test_era_abbreviation(self):
        assert _run("Nel 44 a.c. circa.") == "Nel 44 avanti Cristo circa."

    def test_sentence_initial_capitalized_abbreviation(self):
        # Case-insensitive by default: a sentence-initial "Es." still expands.
        assert _run("Es. pratico qui.") == "esempio pratico qui."


# --------------------------------------------------------------------------
# AC3: optional domain dictionary maps acronyms/terms to spoken forms
# --------------------------------------------------------------------------


class TestDomainDictionary:
    def test_acronym_expands_from_dictionary(self):
        out = _run(
            "Studio l'AI oggi.",
            domain_dictionary={"AI": "intelligenza artificiale"},
        )
        assert out == "Studio l'intelligenza artificiale oggi."

    def test_multiword_term_expands(self):
        out = _run(
            "Uso TTS locale.", domain_dictionary={"TTS": "sintesi vocale"}
        )
        assert out == "Uso sintesi vocale locale."

    def test_domain_matching_is_case_sensitive_by_default(self):
        # The lowercase Italian word "ai" must not collide with the acronym.
        out = _run(
            "Vado ai giardini.",
            domain_dictionary={"AI": "intelligenza artificiale"},
        )
        assert out == "Vado ai giardini."

    def test_domain_case_insensitive_when_enabled(self):
        out = _run(
            "Vado ai giardini.",
            domain_dictionary={"AI": "intelligenza artificiale"},
            params={PARAM_DOMAIN_CASE_INSENSITIVE: True},
        )
        assert out == "Vado intelligenza artificiale giardini."

    def test_domain_does_not_match_inside_a_word(self):
        out = _run("La MAILBOX è piena.", domain_dictionary={"AI": "x"})
        assert out == "La MAILBOX è piena."


# --------------------------------------------------------------------------
# AC4: with no domain dictionary, the built-in set still applies
# --------------------------------------------------------------------------


class TestNoDomainDictionary:
    def test_builtin_applies_without_dictionary(self):
        # No domain_dictionary supplied at all (empty mapping by default).
        assert _run("Compra mele ecc.") == "Compra mele eccetera."

    def test_domain_applies_even_without_language_data(self):
        # Built-in set is a no-op for a language with no data, but a supplied
        # domain dictionary is language-independent and still applies.
        out = _run(
            "ecc. e AI.",
            language_data={},
            domain_dictionary={"AI": "intelligenza artificiale"},
        )
        assert out == "ecc. e intelligenza artificiale."


# --------------------------------------------------------------------------
# No-op without language data
# --------------------------------------------------------------------------


class TestNoLanguageData:
    def test_no_builtin_expansion_for_unknown_language(self):
        assert _run("Mele, pere, ecc.", language_data={}) == "Mele, pere, ecc."


# --------------------------------------------------------------------------
# Whole-token matching and boundaries
# --------------------------------------------------------------------------


class TestBoundaries:
    def test_abbreviation_letters_inside_word_are_left_alone(self):
        # "es" appears inside "espresso" but without the required period.
        assert _run("Un espresso, grazie.") == "Un espresso, grazie."

    def test_abbreviation_glued_to_preceding_word_is_left_alone(self):
        assert _run("Processo res. interno") == "Processo res. interno"


# --------------------------------------------------------------------------
# Sentence-period handling
# --------------------------------------------------------------------------


class TestSentencePeriod:
    def test_period_readded_before_paragraph_break(self):
        assert _run("Lista: mele, ecc.\n\nFine.") == "Lista: mele, eccetera.\n\nFine."

    def test_no_period_when_followed_by_more_text(self):
        assert _run("mele ecc. poi pere") == "mele eccetera poi pere"


# --------------------------------------------------------------------------
# Configurable per-concern switches (model profile params)
# --------------------------------------------------------------------------


class TestConfigurableBehaviors:
    def test_builtin_expansion_can_be_disabled(self):
        assert _run("Mele, ecc.", params={PARAM_EXPAND_ABBREVIATIONS: False}) == (
            "Mele, ecc."
        )

    def test_domain_application_can_be_disabled(self):
        out = _run(
            "Uso AI.",
            domain_dictionary={"AI": "intelligenza artificiale"},
            params={PARAM_APPLY_DOMAIN_DICTIONARY: False},
        )
        assert out == "Uso AI."

    def test_builtin_case_sensitive_when_disabled(self):
        # With case-insensitivity off, the capitalized "Es." no longer matches
        # the lowercase key, while the lowercase form still does.
        assert _run("Es. uno", params={PARAM_ABBREVIATION_CASE_INSENSITIVE: False}) == (
            "Es. uno"
        )
        assert _run("es. uno", params={PARAM_ABBREVIATION_CASE_INSENSITIVE: False}) == (
            "esempio uno"
        )


# --------------------------------------------------------------------------
# Precedence: domain dictionary wins over the built-in set
# --------------------------------------------------------------------------


class TestPrecedence:
    def test_domain_entry_overrides_builtin(self):
        custom_data = {
            LANGUAGE_DATA_NAMESPACE: {ABBREVIATIONS_KEY: {"es.": "esempio"}}
        }
        out = _run(
            "Vedi es. qui.",
            language_data=custom_data,
            domain_dictionary={"es.": "esercizio"},
            params={PARAM_DOMAIN_CASE_INSENSITIVE: True},
        )
        # The domain dictionary is applied first, so its form wins.
        assert out == "Vedi esercizio qui."


# --------------------------------------------------------------------------
# Registration into the default pipeline
# --------------------------------------------------------------------------


class TestDefaultPipelineRegistration:
    def test_stage_registered_under_canonical_name(self):
        assert st.has_stage(STAGE_ABBREVIATION_EXPANSION)

    def test_runs_last_in_the_default_service(self):
        # End-to-end through the service (default language it, default model
        # profile): the abbreviation stage runs after the others.
        result = PreprocessingService().preprocess("Compra mele, pere, ecc.")
        assert result.normalized_text == "Compra mele, pere, eccetera."

    def test_service_expands_after_numeric_stage(self):
        # The numeric stage (3rd) verbalizes the page number, then this stage
        # (4th) expands the abbreviation in the same run.
        result = PreprocessingService().preprocess("Vedi pag. 10.")
        assert result.normalized_text == "Vedi pagina dieci."
