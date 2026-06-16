"""Tests for the numeric & symbolic verbalization stage.

Exercises every acceptance criterion of REQ-F-text-numeric-symbolic-verbalization
against the stage in isolation (a stage is an independently testable unit —
DEC-text-preprocessing-pipeline, REQ-MNT-preprocessing-pipeline AC1): cardinals
and decimals with thousands/decimal separators, full dates, percentages,
currency, common symbols, and Italian-convention spelling (DEC-default-italian-language).
Also covers the configurable per-concern switches, graceful no-op without
language data, and registration into the default pipeline.
"""

from __future__ import annotations

import pytest

from local_tts.preprocessing import profiles as pr
from local_tts.preprocessing import stages as st
from local_tts.preprocessing.numeric_symbolic_verbalization import (
    BUILTIN_LANGUAGE_DATA,
    LANGUAGE_DATA_NAMESPACE,
    NumericSymbolicVerbalizationStage,
    PARAM_VERBALIZE_CURRENCY,
    PARAM_VERBALIZE_DATES,
    PARAM_VERBALIZE_NUMBERS,
    PARAM_VERBALIZE_ORDINALS,
    PARAM_VERBALIZE_PERCENT,
    PARAM_VERBALIZE_SYMBOLS,
    PARAM_VERBALIZE_TEMPERATURE,
)
from local_tts.preprocessing.service import PreprocessingService
from local_tts.preprocessing.stages import (
    STAGE_NUMERIC_SYMBOLIC_VERBALIZATION,
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


def _stage() -> NumericSymbolicVerbalizationStage:
    return NumericSymbolicVerbalizationStage()


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
        assert _stage().name == STAGE_NUMERIC_SYMBOLIC_VERBALIZATION

    def test_empty_string_passthrough(self):
        assert _run("") == ""

    def test_text_without_numbers_or_symbols_unchanged(self):
        text = "Questa frase non contiene nulla da verbalizzare."
        assert _run(text) == text

    def test_no_op_without_language_data(self):
        # An unknown language resolves to an empty profile; the stage must then
        # leave everything untouched rather than guess.
        assert _run("Costa 25% in 1.234,56 €.", language_data={}) == (
            "Costa 25% in 1.234,56 €."
        )


# --------------------------------------------------------------------------
# AC1: cardinals/decimals with thousands and decimal separators
# --------------------------------------------------------------------------


class TestNumbers:
    def test_plain_integer(self):
        assert _run("Ho 42 anni.") == "Ho quarantadue anni."

    def test_thousands_separator_grouped_number(self):
        assert _run("Sono 1.234 persone.") == "Sono milleduecentotrentaquattro persone."

    def test_thousands_and_decimal(self):
        # AC1: read as the full spoken number, not digit-by-digit or skipped.
        assert _run("Totale 1.234,56 unità.") == (
            "Totale milleduecentotrentaquattro virgola cinque sei unità."
        )

    def test_decimal_digit_by_digit_tail(self):
        assert _run("Pi greco vale 3,14.") == "Pi greco vale tre virgola uno quattro."

    def test_negative_number(self):
        assert _run("Fa -5 stanotte.") == "Fa meno cinque stanotte."

    def test_number_glued_to_letters_is_left_alone(self):
        # Avoid mangling identifiers / version-like tokens.
        assert _run("Modello A4 pronto.") == "Modello A4 pronto."

    def test_separators_are_language_config_driven(self):
        # The English convention (thousands ",", decimal ".") is selected purely
        # by language data — no language branching in the stage.
        en_data = {
            LANGUAGE_DATA_NAMESPACE: {
                "num2words_lang": "en",
                "thousands_separator": ",",
                "decimal_separator": ".",
                "decimal_word": "point",
            }
        }
        assert _run("It is 1,234.56 today.", language_data=en_data) == (
            "It is one thousand, two hundred and thirty-four point five six today."
        )


# --------------------------------------------------------------------------
# AC2: dates written in full
# --------------------------------------------------------------------------


class TestDates:
    def test_slash_date(self):
        assert _run("Il 15/03/2026 partiamo.") == (
            "Il quindici marzo duemilaventisei partiamo."
        )

    def test_dash_date(self):
        assert _run("Scadenza 15-03-2026.") == (
            "Scadenza quindici marzo duemilaventisei."
        )

    def test_first_of_month_is_ordinal(self):
        assert _run("Nato il 01/01/2000.") == "Nato il primo gennaio duemila."

    def test_invalid_date_is_not_treated_as_a_date(self):
        # Month 13 / day 32 is not a date; it must not be force-read as one.
        out = _run("Codice 32/13/2026 interno.")
        assert "marzo" not in out
        assert "32" not in out and "13" not in out  # still verbalized as numbers


# --------------------------------------------------------------------------
# AC3: percentages and currency symbols read as words
# --------------------------------------------------------------------------


class TestPercent:
    def test_percentage(self):
        assert _run("Sconto del 25%.") == "Sconto del venticinque per cento."

    def test_decimal_percentage(self):
        assert _run("Cresce del 2,5%.") == "Cresce del due virgola cinque per cento."

    def test_per_mille(self):
        assert _run("Tasso 3‰.") == "Tasso tre per mille."


class TestCurrency:
    def test_symbol_before_amount(self):
        assert _run("Costa €10.") == "Costa dieci euro."

    def test_symbol_after_amount(self):
        assert _run("Costa 10€.") == "Costa dieci euro."

    def test_amount_with_cents(self):
        assert _run("Prezzo €10,50.") == "Prezzo dieci euro e cinquanta centesimi."

    def test_singular_uses_elided_form(self):
        assert _run("Solo €1.") == "Solo un euro."

    def test_cents_only_reads_as_cents(self):
        assert _run("Appena €0,99.") == "Appena novantanove centesimi."

    def test_thousands_amount(self):
        assert _run("Vale 1.234,56 €.") == (
            "Vale milleduecentotrentaquattro euro e cinquantasei centesimi."
        )

    def test_other_currency(self):
        assert _run("Paga $5.") == "Paga cinque dollari."


# --------------------------------------------------------------------------
# AC4: Italian conventions (elision, ordinals)
# --------------------------------------------------------------------------


class TestItalianConventions:
    def test_elided_twenties(self):
        assert _run("Ha 21 anni e ne aveva 28.") == (
            "Ha ventuno anni e ne aveva ventotto."
        )

    def test_masculine_ordinal_indicator(self):
        assert _run("Il 1° piano.") == "Il primo piano."

    def test_feminine_ordinal_indicator(self):
        assert _run("La 2ª guerra.") == "La seconda guerra."

    def test_higher_ordinal(self):
        assert _run("Il 20° secolo.") == "Il ventesimo secolo."


# --------------------------------------------------------------------------
# Temperature
# --------------------------------------------------------------------------


class TestTemperature:
    def test_celsius(self):
        assert _run("Sono 20°C oggi.") == "Sono venti gradi Celsius oggi."

    def test_celsius_with_spaces(self):
        assert _run("Sono 20 °C oggi.") == "Sono venti gradi Celsius oggi."

    def test_fahrenheit(self):
        assert _run("Sono 451°F.") == (
            "Sono quattrocentocinquantuno gradi Fahrenheit."
        )


# --------------------------------------------------------------------------
# Other common symbols read as words
# --------------------------------------------------------------------------


class TestSymbols:
    def test_ampersand(self):
        assert _run("Tom & Jerry.") == "Tom e Jerry."

    def test_plus_between_numbers(self):
        assert _run("2+2 fa quattro.") == "due più due fa quattro."

    def test_equals(self):
        assert _run("a = b") == "a uguale b"

    def test_at_sign(self):
        assert _run("scrivi @ qui") == "scrivi chiocciola qui"


# --------------------------------------------------------------------------
# Configurable per-concern switches (model profile params)
# --------------------------------------------------------------------------


class TestConfigurableBehaviors:
    def test_dates_can_be_disabled(self):
        # With dates off, the digit groups fall through to plain-number
        # verbalization; the date semantics (the month name) are not applied.
        out = _run("Il 15/03/2026.", params={PARAM_VERBALIZE_DATES: False})
        assert "marzo" not in out
        assert out == "Il quindici/tre/duemilaventisei."

    def test_currency_can_be_disabled(self):
        out = _run("Costa €10.", params={PARAM_VERBALIZE_CURRENCY: False})
        assert "€" in out and "euro" not in out

    def test_percent_can_be_disabled(self):
        out = _run("Sconto 25%.", params={PARAM_VERBALIZE_PERCENT: False})
        assert "%" in out and "per cento" not in out

    def test_temperature_can_be_disabled(self):
        out = _run("Sono 20°C.", params={PARAM_VERBALIZE_TEMPERATURE: False})
        assert "gradi" not in out

    def test_ordinals_can_be_disabled(self):
        out = _run("Il 1° piano.", params={PARAM_VERBALIZE_ORDINALS: False})
        assert "primo" not in out

    def test_numbers_can_be_disabled(self):
        assert _run("Ho 42 anni.", params={PARAM_VERBALIZE_NUMBERS: False}) == (
            "Ho 42 anni."
        )

    def test_symbols_can_be_disabled(self):
        assert _run("Tom & Jerry.", params={PARAM_VERBALIZE_SYMBOLS: False}) == (
            "Tom & Jerry."
        )


# --------------------------------------------------------------------------
# Boundary preservation
# --------------------------------------------------------------------------


class TestBoundaryPreservation:
    def test_paragraph_boundaries_survive(self):
        text = "Primo 5.\n\nSecondo 6."
        assert _run(text) == "Primo cinque.\n\nSecondo sei."


# --------------------------------------------------------------------------
# Registration into the default pipeline
# --------------------------------------------------------------------------


class TestDefaultPipelineRegistration:
    def test_stage_registered_under_canonical_name(self):
        assert st.has_stage(STAGE_NUMERIC_SYMBOLIC_VERBALIZATION)

    def test_runs_in_the_default_service_after_layout(self):
        # End-to-end through the service (default language it, default model
        # profile): Unicode + layout normalize, then this stage verbalizes.
        raw = "Costa 1.234,56 € il 15/03/2026."
        result = PreprocessingService().preprocess(raw)
        assert result.normalized_text == (
            "Costa milleduecentotrentaquattro euro e cinquantasei centesimi "
            "il quindici marzo duemilaventisei."
        )
