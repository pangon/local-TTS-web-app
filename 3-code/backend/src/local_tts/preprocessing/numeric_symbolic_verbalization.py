"""Numeric & symbolic verbalization stage — the third preprocessing stage.

Transcribes numeric and symbolic content into spelled-out words appropriate to
the output language (``REQ-F-text-numeric-symbolic-verbalization``); the third
stage of the default pipeline, running after layout repair and before
abbreviation expansion (``DEC-text-preprocessing-pipeline``).  In order, the
stage verbalizes:

1. **Dates** written with ``/`` or ``-`` separators
   (``15/03/2026`` → "quindici marzo duemilaventisei").
2. **Currency** amounts
   (``€10,50`` → "dieci euro e cinquanta centesimi").
3. **Percentages** and per-mille (``25%`` → "venticinque per cento").
4. **Temperatures** (``20°C`` → "venti gradi Celsius").
5. **Ordinal indicators** (``1°`` → "primo", ``2ª`` → "seconda").
6. **Plain cardinals and decimals**, honouring the language's thousands/decimal
   separators (``1.234,56`` → "milleduecentotrentaquattro virgola cinque sei").
7. **Standalone symbols** read as words (``&`` → "e", ``+`` → "più", …).

Number spelling itself is delegated to :mod:`num2words` (LGPL), selected by the
language's ``num2words`` code carried in the language profile — so the shared
``run`` logic never branches on a specific language.  Every language-specific
table (separators, spoken words, month names, currency/percent/symbol words,
ordinal indicators) arrives through the resolved :class:`StageConfig`'s
``language_data`` namespace, exposed for the default language as
:data:`BUILTIN_LANGUAGE_DATA`; behaviour switches arrive through the model
profile's ``params`` via ``PARAM_*`` constants
(``DEC-text-preprocessing-pipeline``).  Without language data for the configured
language the stage is a no-op, so unknown languages pass through unchanged
(mirroring :func:`~local_tts.preprocessing.profiles.resolve_language_profile`'s
empty-profile fallback).

The exact patterns are deliberately conservative and refined through testing
(``REQ-F-text-numeric-symbolic-verbalization``).  Known heuristics: ``N°`` is
read as a masculine ordinal — the dominant Italian usage (e.g. "il 1° piano") —
unless followed by ``C``/``F`` (temperature); dates validate day ≤ 31 and
month ≤ 12 to avoid mis-reading numeric ranges; decimals are read digit by digit
after the decimal word (the num2words convention); separator conventions are
language-config-driven, so a number written against another language's
convention may be mis-grouped.
"""

from __future__ import annotations

import re
from typing import Any, Mapping

from num2words import num2words

from local_tts.preprocessing.stages import (
    STAGE_NUMERIC_SYMBOLIC_VERBALIZATION,
    StageConfig,
)

# Namespace this stage owns within a language profile's ``data`` mapping.  Each
# stage reads only its own namespace so several stages can contribute to the
# same language without colliding (see ``profiles.register_language_data``).
LANGUAGE_DATA_NAMESPACE = STAGE_NUMERIC_SYMBOLIC_VERBALIZATION

# --- Language-data keys (read from the stage's namespace). ------------------
# The language code passed to num2words for the actual spelling.  Its presence
# is what "activates" the stage for a language.
NUM2WORDS_LANG_KEY = "num2words_lang"
THOUSANDS_SEPARATOR_KEY = "thousands_separator"
DECIMAL_SEPARATOR_KEY = "decimal_separator"
DECIMAL_WORD_KEY = "decimal_word"
MINUS_WORD_KEY = "minus_word"
PERCENT_WORDS_KEY = "percent_words"  # {symbol: spoken form}
DEGREE_WORD_KEY = "degree_word"
TEMPERATURE_SCALES_KEY = "temperature_scales"  # {"C": "Celsius", ...}
MONTH_NAMES_KEY = "month_names"  # {1: "gennaio", ...}
ORDINAL_MASCULINE_INDICATORS_KEY = "ordinal_masculine_indicators"
ORDINAL_FEMININE_INDICATORS_KEY = "ordinal_feminine_indicators"
ORDINAL_FEMININE_ENDING_KEY = "ordinal_feminine_ending"
CURRENCIES_KEY = "currencies"  # {symbol: {one/singular/plural/cents_*}}
CENTS_CONJUNCTION_KEY = "cents_conjunction"
SYMBOL_WORDS_KEY = "symbol_words"  # {symbol: spoken word}

# --- Model-profile parameter names and defaults. ---------------------------
# Each distinct concern can be toggled by a model profile without touching this
# shared logic; every behaviour defaults to on — that is the stage's purpose.
PARAM_VERBALIZE_DATES = "verbalize_dates"
PARAM_VERBALIZE_CURRENCY = "verbalize_currency"
PARAM_VERBALIZE_PERCENT = "verbalize_percent"
PARAM_VERBALIZE_TEMPERATURE = "verbalize_temperature"
PARAM_VERBALIZE_ORDINALS = "verbalize_ordinals"
PARAM_VERBALIZE_NUMBERS = "verbalize_numbers"
PARAM_VERBALIZE_SYMBOLS = "verbalize_symbols"

# --- Universal structural recognizers. -------------------------------------
# A numeric run for the contextual passes (currency/percent/temperature): it
# must end in a digit so a trailing separator or period is never swallowed.
_AMOUNT = r"\d[\d.,]*\d|\d"

# Dates: dd<sep>mm<sep>yyyy, same separator twice; not glued to other digits.
_DATE_RE = re.compile(r"(?<!\d)(\d{1,2})([/-])(\d{1,2})\2(\d{2,4})(?!\d)")

# Horizontal whitespace (everything but the newline that delimits paragraphs).
_HWS_RUN_RE = re.compile(r"[^\S\n]+")
_HWS_AROUND_NL_RE = re.compile(r"[^\S\n]*\n[^\S\n]*")


# Italian language tables (``DEC-default-italian-language``).  This is data
# carried by the language profile, not logic — adding a language means adding a
# table here (and a num2words-supported code), never editing the stage
# (``DEC-text-preprocessing-pipeline``).
BUILTIN_LANGUAGE_DATA: dict[str, dict[str, Any]] = {
    "it": {
        LANGUAGE_DATA_NAMESPACE: {
            NUM2WORDS_LANG_KEY: "it",
            THOUSANDS_SEPARATOR_KEY: ".",
            DECIMAL_SEPARATOR_KEY: ",",
            DECIMAL_WORD_KEY: "virgola",
            MINUS_WORD_KEY: "meno",
            PERCENT_WORDS_KEY: {"%": "per cento", "‰": "per mille"},
            DEGREE_WORD_KEY: "gradi",
            TEMPERATURE_SCALES_KEY: {"C": "Celsius", "F": "Fahrenheit"},
            MONTH_NAMES_KEY: {
                1: "gennaio",
                2: "febbraio",
                3: "marzo",
                4: "aprile",
                5: "maggio",
                6: "giugno",
                7: "luglio",
                8: "agosto",
                9: "settembre",
                10: "ottobre",
                11: "novembre",
                12: "dicembre",
            },
            ORDINAL_MASCULINE_INDICATORS_KEY: "°º",
            ORDINAL_FEMININE_INDICATORS_KEY: "ª",
            ORDINAL_FEMININE_ENDING_KEY: "a",
            CENTS_CONJUNCTION_KEY: "e",
            CURRENCIES_KEY: {
                "€": {
                    "one": "un euro",
                    "singular": "euro",
                    "plural": "euro",
                    "cents_one": "un centesimo",
                    "cents_singular": "centesimo",
                    "cents_plural": "centesimi",
                },
                "$": {
                    "one": "un dollaro",
                    "singular": "dollaro",
                    "plural": "dollari",
                    "cents_one": "un centesimo",
                    "cents_singular": "centesimo",
                    "cents_plural": "centesimi",
                },
                "£": {
                    "one": "una sterlina",
                    "singular": "sterlina",
                    "plural": "sterline",
                    "cents_one": "un penny",
                    "cents_singular": "penny",
                    "cents_plural": "penny",
                },
                "¥": {
                    "one": "uno yen",
                    "singular": "yen",
                    "plural": "yen",
                },
            },
            SYMBOL_WORDS_KEY: {
                "&": "e",
                "+": "più",
                "=": "uguale",
                "@": "chiocciola",
                "#": "cancelletto",
                "§": "paragrafo",
                "*": "asterisco",
            },
        }
    }
}


class NumericSymbolicVerbalizationStage:
    """Verbalizes numbers, dates, currency, and symbols before synthesis.

    Stateless and shared across requests; all per-request variation (language
    data, model parameters) arrives through :class:`StageConfig`.
    """

    name = STAGE_NUMERIC_SYMBOLIC_VERBALIZATION

    def run(self, text: str, config: StageConfig) -> str:
        if not text:
            return text

        ns = config.language_data.get(LANGUAGE_DATA_NAMESPACE)
        if not isinstance(ns, Mapping) or not ns:
            return text
        lang = ns.get(NUM2WORDS_LANG_KEY)
        if not lang:
            return text

        params = config.params
        # Order matters: contextual passes (date/currency/percent/temperature/
        # ordinal) consume their digits first, so the plain-number pass only
        # ever sees genuinely bare numbers.
        if params.get(PARAM_VERBALIZE_DATES, True):
            text = self._verbalize_dates(text, ns, lang)
        if params.get(PARAM_VERBALIZE_CURRENCY, True):
            text = self._verbalize_currency(text, ns, lang)
        if params.get(PARAM_VERBALIZE_PERCENT, True):
            text = self._verbalize_percent(text, ns, lang)
        if params.get(PARAM_VERBALIZE_TEMPERATURE, True):
            text = self._verbalize_temperature(text, ns, lang)
        if params.get(PARAM_VERBALIZE_ORDINALS, True):
            text = self._verbalize_ordinals(text, ns, lang)
        if params.get(PARAM_VERBALIZE_NUMBERS, True):
            text = self._verbalize_numbers(text, ns, lang)
        if params.get(PARAM_VERBALIZE_SYMBOLS, True):
            text = self._verbalize_symbols(text, ns)

        return _tidy_spaces(text)

    # -- individual passes (each independently exercisable) -----------------

    @staticmethod
    def _verbalize_dates(text: str, ns: Mapping[str, Any], lang: str) -> str:
        months = ns.get(MONTH_NAMES_KEY)
        if not isinstance(months, Mapping):
            return text

        def repl(m: re.Match[str]) -> str:
            day, month, year = int(m.group(1)), int(m.group(3)), int(m.group(4))
            name = months.get(month, months.get(str(month)))
            if name is None or not 1 <= day <= 31:
                return m.group(0)
            # The first of the month is ordinal in Italian ("il primo marzo").
            day_words = (
                _spell_ordinal(day, lang) if day == 1 else _spell_cardinal(day, lang)
            )
            year_words = _spell_cardinal(year, lang)
            if day_words is None or year_words is None:
                return m.group(0)
            return f"{day_words} {name} {year_words}"

        return _DATE_RE.sub(repl, text)

    @staticmethod
    def _verbalize_currency(text: str, ns: Mapping[str, Any], lang: str) -> str:
        currencies = ns.get(CURRENCIES_KEY)
        if not isinstance(currencies, Mapping) or not currencies:
            return text
        conjunction = ns.get(CENTS_CONJUNCTION_KEY, "")
        symbol_class = _char_class(currencies)

        def phrase(symbol: str, amount: str) -> str | None:
            entry = currencies.get(symbol)
            if not isinstance(entry, Mapping):
                return None
            parsed = _parse_amount(amount, ns)
            if parsed is None:
                return None
            euros, cents = parsed
            return _money_phrase(euros, cents, entry, conjunction, lang)

        # Symbol-before ("€10") then symbol-after ("10€"); the first pass
        # removes the symbol, so the second never double-counts.
        before = re.compile(rf"([{symbol_class}])\s?({_AMOUNT})")
        text = before.sub(
            lambda m: phrase(m.group(1), m.group(2)) or m.group(0), text
        )
        after = re.compile(rf"({_AMOUNT})\s?([{symbol_class}])")
        text = after.sub(
            lambda m: phrase(m.group(2), m.group(1)) or m.group(0), text
        )
        return text

    @staticmethod
    def _verbalize_percent(text: str, ns: Mapping[str, Any], lang: str) -> str:
        percents = ns.get(PERCENT_WORDS_KEY)
        if not isinstance(percents, Mapping) or not percents:
            return text
        pattern = re.compile(rf"({_AMOUNT})\s?([{_char_class(percents)}])")

        def repl(m: re.Match[str]) -> str:
            words = _spell_number_token(m.group(1), ns, lang)
            word = percents.get(m.group(2))
            if words is None or word is None:
                return m.group(0)
            return f"{words} {word}"

        return pattern.sub(repl, text)

    @staticmethod
    def _verbalize_temperature(text: str, ns: Mapping[str, Any], lang: str) -> str:
        degree = ns.get(DEGREE_WORD_KEY)
        scales = ns.get(TEMPERATURE_SCALES_KEY)
        if not degree or not isinstance(scales, Mapping) or not scales:
            return text
        pattern = re.compile(
            rf"({_AMOUNT})\s?°\s?([{_char_class(scales)}])\b"
        )

        def repl(m: re.Match[str]) -> str:
            words = _spell_number_token(m.group(1), ns, lang)
            scale = scales.get(m.group(2))
            if words is None or scale is None:
                return m.group(0)
            return f"{words} {degree} {scale}"

        return pattern.sub(repl, text)

    @staticmethod
    def _verbalize_ordinals(text: str, ns: Mapping[str, Any], lang: str) -> str:
        masculine = ns.get(ORDINAL_MASCULINE_INDICATORS_KEY, "")
        feminine = ns.get(ORDINAL_FEMININE_INDICATORS_KEY, "")
        feminine_ending = ns.get(ORDINAL_FEMININE_ENDING_KEY, "")
        indicators = f"{masculine}{feminine}"
        if not indicators:
            return text
        pattern = re.compile(rf"(\d+)([{re.escape(indicators)}])")

        def repl(m: re.Match[str]) -> str:
            word = _spell_ordinal(int(m.group(1)), lang)
            if word is None:
                return m.group(0)
            if m.group(2) in feminine and feminine_ending:
                word = word[:-1] + feminine_ending
            return word

        return pattern.sub(repl, text)

    @staticmethod
    def _verbalize_numbers(text: str, ns: Mapping[str, Any], lang: str) -> str:
        thousands = re.escape(ns.get(THOUSANDS_SEPARATOR_KEY, ""))
        decimal = re.escape(ns.get(DECIMAL_SEPARATOR_KEY, "."))
        if thousands:
            number = (
                rf"\d{{1,3}}(?:{thousands}\d{{3}})+(?:{decimal}\d+)?"
                rf"|\d+(?:{decimal}\d+)?"
            )
        else:
            number = rf"\d+(?:{decimal}\d+)?"
        pattern = re.compile(rf"(?<!\w)(-?(?:{number}))(?!\w)")

        def repl(m: re.Match[str]) -> str:
            words = _spell_number_token(m.group(1), ns, lang)
            return words if words is not None else m.group(0)

        return pattern.sub(repl, text)

    @staticmethod
    def _verbalize_symbols(text: str, ns: Mapping[str, Any]) -> str:
        symbols = ns.get(SYMBOL_WORDS_KEY)
        if not isinstance(symbols, Mapping) or not symbols:
            return text
        pattern = re.compile(rf"[{_char_class(symbols)}]")
        # Space-pad the spoken word; _tidy_spaces (run last) absorbs the
        # padding, like the Unicode stage does for verbalized emoji.
        return pattern.sub(lambda m: f" {symbols[m.group(0)]} ", text)


# ---------------------------------------------------------------------------
# Module-level helpers (pure; no language branching)
# ---------------------------------------------------------------------------


def _char_class(symbols: Mapping[str, Any]) -> str:
    """Escape the keys of *symbols* into a regex character-class body."""
    return "".join(re.escape(s) for s in symbols)


def _spell_cardinal(value: int, lang: str) -> str | None:
    """Spell *value* as a cardinal in *lang*, or ``None`` if unsupported."""
    try:
        return num2words(value, lang=lang)
    except Exception:  # num2words raises for unsupported languages / inputs
        return None


def _spell_ordinal(value: int, lang: str) -> str | None:
    """Spell *value* as an ordinal in *lang*, or ``None`` if unsupported."""
    try:
        return num2words(value, lang=lang, to="ordinal")
    except Exception:
        return None


def _spell_digits(digits: str, lang: str) -> str | None:
    """Spell each digit of *digits* individually (decimal-tail convention)."""
    words: list[str] = []
    for ch in digits:
        word = _spell_cardinal(int(ch), lang)
        if word is None:
            return None
        words.append(word)
    return " ".join(words)


def _split_number(token: str, ns: Mapping[str, Any]) -> tuple[bool, str, str] | None:
    """Split a numeric *token* into (negative, integer digits, fraction digits).

    Thousands separators are removed; the decimal separator splits off the
    fractional part.  Returns ``None`` when the token is not a clean number
    under the configured separators.
    """
    thousands = ns.get(THOUSANDS_SEPARATOR_KEY, "")
    decimal = ns.get(DECIMAL_SEPARATOR_KEY, ".")
    negative = token.startswith("-")
    body = token[1:] if negative else token
    if decimal and decimal in body:
        integer, _, fraction = body.partition(decimal)
    else:
        integer, fraction = body, ""
    if thousands:
        integer = integer.replace(thousands, "")
    if not integer.isdigit() or (fraction and not fraction.isdigit()):
        return None
    return negative, integer, fraction


def _spell_number_token(token: str, ns: Mapping[str, Any], lang: str) -> str | None:
    """Spell a full numeric token (sign, thousands groups, decimal) as words."""
    split = _split_number(token, ns)
    if split is None:
        return None
    negative, integer, fraction = split

    integer_words = _spell_cardinal(int(integer), lang)
    if integer_words is None:
        return None

    parts: list[str] = []
    minus_word = ns.get(MINUS_WORD_KEY, "")
    if negative and minus_word:
        parts.append(minus_word)
    parts.append(integer_words)

    if fraction:
        fraction_words = _spell_digits(fraction, lang)
        if fraction_words is None:
            return None
        decimal_word = ns.get(DECIMAL_WORD_KEY, "")
        if decimal_word:
            parts.append(decimal_word)
        parts.append(fraction_words)

    return " ".join(parts)


def _parse_amount(amount: str, ns: Mapping[str, Any]) -> tuple[int, int | None] | None:
    """Parse a currency *amount* into (major units, minor units or ``None``)."""
    split = _split_number(amount, ns)
    if split is None:
        return None
    _negative, integer, fraction = split
    major = int(integer)
    minor = int((fraction + "00")[:2]) if fraction else None
    return major, minor


def _count_phrase(
    value: int, entry: Mapping[str, Any], kind: str, lang: str
) -> str | None:
    """Spell *value* with the matching noun form from a currency *entry*.

    *kind* is ``"main"`` (major units) or ``"cents"`` (minor units).  A
    language may supply an explicit ``one``/``cents_one`` elided form (Italian
    "un euro" rather than "uno euro"); otherwise the singular noun is used for
    1 and the plural otherwise.
    """
    prefix = "" if kind == "main" else "cents_"
    if value == 1 and entry.get(f"{prefix}one"):
        return entry[f"{prefix}one"]
    noun = entry.get(f"{prefix}singular" if value == 1 else f"{prefix}plural")
    if noun is None:
        return None
    words = _spell_cardinal(value, lang)
    if words is None:
        return None
    return f"{words} {noun}"


def _money_phrase(
    major: int,
    minor: int | None,
    entry: Mapping[str, Any],
    conjunction: str,
    lang: str,
) -> str | None:
    """Build the spoken form of a currency amount from its parsed parts."""
    # "0,99 €" reads better as just the cents ("novantanove centesimi").
    if major == 0 and minor:
        return _count_phrase(minor, entry, "cents", lang)

    major_words = _count_phrase(major, entry, "main", lang)
    if major_words is None:
        return None
    if not minor:
        return major_words

    minor_words = _count_phrase(minor, entry, "cents", lang)
    if minor_words is None:
        return major_words
    parts = [major_words]
    if conjunction:
        parts.append(conjunction)
    parts.append(minor_words)
    return " ".join(parts)


def _tidy_spaces(text: str) -> str:
    """Collapse the horizontal whitespace this stage may have introduced.

    Verbalized symbols are space-padded, so a final tidy keeps the output
    clean without disturbing the paragraph boundaries (blank lines) that the
    layout-repair stage established: only horizontal whitespace runs are
    collapsed, and spaces hugging a newline are trimmed.
    """
    text = _HWS_RUN_RE.sub(" ", text)
    text = _HWS_AROUND_NL_RE.sub("\n", text)
    return text.strip(" ")
