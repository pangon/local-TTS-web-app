"""Unicode sanitization stage — the first preprocessing stage.

Cleans character-level anomalies that would otherwise corrupt or degrade the
synthesized audio (``REQ-F-text-unicode-sanitization``); the first stage of the
default pipeline (``DEC-text-preprocessing-pipeline``).  In order, the stage:

1. Applies Unicode normalization (``NFC`` by default) so accented letters and
   the like are in a canonical, composed form.
2. Normalizes line endings (CRLF/CR, vertical tab, form feed, U+2028/U+2029) to
   ``\\n`` so paragraph and chapter boundaries survive for the downstream
   layout-repair stage (``REQ-F-text-layout-repair``).
3. Removes or verbalizes emoji, per configuration.
4. Normalizes dash variants (em/en/figure dash, horizontal bar, minus sign, …)
   to a single configurable form (hyphen-minus by default).
5. Normalizes smart/typographic quotes, guillemets, and primes to straight
   ASCII quotes.
6. Removes invisible / disallowed code points — control (``Cc``, except the
   structural tab and newline), format (``Cf`` — covers zero-width spaces, the
   soft hyphen, the BOM, and bidi marks), surrogate (``Cs``), and private-use
   (``Co``) — and converts non-breaking spaces and other Unicode space
   separators (``Zs``) plus tabs to a normal space.  Collapsing runs of
   whitespace is deliberately left to the layout-repair stage.

The stage carries only **universal** Unicode tables.  Language-specific data
(spoken emoji names) arrives through the resolved :class:`StageConfig`'s
``language_data``; behavior switches (emoji mode, dash form, normalization
form) through the model profile's ``params`` — no language- or model-specific
rule is hardcoded into the shared logic (``DEC-text-preprocessing-pipeline``).

The exact character classes are refined through testing
(``REQ-F-text-unicode-sanitization``); the tables below are the starting
defaults.
"""

from __future__ import annotations

import re
import unicodedata
from typing import Any, Mapping

from local_tts.preprocessing.stages import (
    STAGE_UNICODE_SANITIZATION,
    StageConfig,
)

# Namespace this stage owns within a language profile's ``data`` mapping.  Each
# stage reads only its own namespace so several stages can contribute to the
# same language without colliding (see ``profiles.register_language_data``).
LANGUAGE_DATA_NAMESPACE = STAGE_UNICODE_SANITIZATION

# Key, inside this stage's language-data namespace, of the emoji -> spoken-word
# table used when ``emoji_mode`` is "verbalize".
EMOJI_NAMES_KEY = "emoji_names"

# --- Model-profile parameter names and accepted values. --------------------
PARAM_EMOJI_MODE = "emoji_mode"
EMOJI_MODE_REMOVE = "remove"
EMOJI_MODE_VERBALIZE = "verbalize"
DEFAULT_EMOJI_MODE = EMOJI_MODE_REMOVE

PARAM_DASH_REPLACEMENT = "dash_replacement"
DEFAULT_DASH_REPLACEMENT = "-"

PARAM_UNICODE_FORM = "unicode_form"
DEFAULT_UNICODE_FORM = "NFC"
_VALID_UNICODE_FORMS = frozenset({"NFC", "NFD", "NFKC", "NFKD"})

# --- Universal character tables. -------------------------------------------

# Line-break variants collapsed to "\n".  CRLF is handled by a prior replace so
# it does not become a double newline.
_LINEBREAK_TABLE: dict[int, str] = {
    0x000D: "\n",  # carriage return (lone)
    0x000B: "\n",  # vertical tab
    0x000C: "\n",  # form feed (often a page break)
    0x2028: "\n",  # line separator
    0x2029: "\n",  # paragraph separator
}

# Dash-like code points normalized to the configured replacement.
_DASH_ORDINALS: tuple[int, ...] = (
    0x2010,  # hyphen
    0x2011,  # non-breaking hyphen
    0x2012,  # figure dash
    0x2013,  # en dash
    0x2014,  # em dash
    0x2015,  # horizontal bar
    0x2043,  # hyphen bullet
    0x2212,  # minus sign
    0xFE58,  # small em dash
    0xFE63,  # small hyphen-minus
    0xFF0D,  # fullwidth hyphen-minus
)

# Smart/typographic quotes, guillemets, and primes -> straight ASCII quotes.
_QUOTE_TABLE: dict[int, str] = {
    # Double quotes
    0x201C: '"',  # left double quotation mark
    0x201D: '"',  # right double quotation mark
    0x201E: '"',  # double low-9 quotation mark
    0x201F: '"',  # double high-reversed-9 quotation mark
    0x00AB: '"',  # left-pointing double angle quotation mark (guillemet)
    0x00BB: '"',  # right-pointing double angle quotation mark (guillemet)
    0x2033: '"',  # double prime
    0x2036: '"',  # reversed double prime
    0x301D: '"',  # reversed double prime quotation mark
    0x301E: '"',  # double prime quotation mark
    0x301F: '"',  # low double prime quotation mark
    0xFF02: '"',  # fullwidth quotation mark
    # Single quotes / apostrophes
    0x2018: "'",  # left single quotation mark
    0x2019: "'",  # right single quotation mark (also apostrophe)
    0x201A: "'",  # single low-9 quotation mark
    0x201B: "'",  # single high-reversed-9 quotation mark
    0x2032: "'",  # prime
    0x2035: "'",  # reversed prime
    0x2039: "'",  # single left-pointing angle quotation mark
    0x203A: "'",  # single right-pointing angle quotation mark
    0x00B4: "'",  # acute accent (mistaken for apostrophe)
    0x02BC: "'",  # modifier letter apostrophe
    0xFF07: "'",  # fullwidth apostrophe
}

# Code points removed entirely when a model profile's ``params`` does not ask
# for verbalization — the main emoji blocks.  This is a deliberate
# approximation (``re``/``unicodedata`` do not expose the Unicode Emoji
# property) refined through testing.
_EMOJI_RE = re.compile(
    "["
    "\U0001F000-\U0001FAFF"  # emoticons, pictographs, transport, supplemental, extended-A, regional indicators
    "\U00002600-\U000026FF"  # miscellaneous symbols
    "\U00002700-\U000027BF"  # dingbats
    "\U00002B00-\U00002BFF"  # miscellaneous symbols and arrows (stars, etc.)
    "\U0000FE00-\U0000FE0F"  # variation selectors
    "]+",
    flags=re.UNICODE,
)

# Joiner / presentation code points skipped when naming an emoji sequence.
_EMOJI_JOINERS = frozenset("️‍")


# Italian spoken names for a small set of common single-code-point emoji
# (``DEC-default-italian-language``).  This is data carried by the language
# profile, not logic — additional languages/emoji are added by registering more
# data, never by editing this stage (``DEC-text-preprocessing-pipeline``).  For
# emoji absent from the table the stage falls back to the Unicode name.
BUILTIN_LANGUAGE_DATA: dict[str, dict[str, Any]] = {
    "it": {
        LANGUAGE_DATA_NAMESPACE: {
            EMOJI_NAMES_KEY: {
                "\U0001F600": "faccina sorridente",
                "\U0001F601": "faccina sorridente",
                "\U0001F603": "faccina sorridente",
                "\U0001F604": "faccina sorridente",
                "\U0001F60A": "faccina sorridente",
                "\U0001F642": "faccina sorridente",
                "\U0001F609": "faccina che fa l'occhiolino",
                "\U0001F602": "faccina che ride",
                "\U0001F923": "faccina che ride",
                "\U0001F62D": "faccina che piange",
                "\U0001F614": "faccina pensierosa",
                "\U0001F44D": "pollice in su",
                "\U0001F44E": "pollice in giù",
                "\U0001F44F": "applausi",
                "\U0001F64F": "mani giunte",
                "\U00002764": "cuore",
                "\U0001F496": "cuore",
                "\U0001F525": "fuoco",
                "\U00002B50": "stella",
                "\U00002705": "segno di spunta",
                "\U0000274C": "croce",
            }
        }
    }
}


class UnicodeSanitizationStage:
    """Removes character-level anomalies before synthesis.

    Stateless and shared across requests; all per-request variation
    (language, model) arrives through :class:`StageConfig`.
    """

    name = STAGE_UNICODE_SANITIZATION

    def run(self, text: str, config: StageConfig) -> str:
        if not text:
            return text

        text = self._normalize_form(text, config)
        text = self._normalize_line_endings(text)
        text = self._handle_emoji(text, config)
        text = self._normalize_punctuation(text, config)
        text = self._filter_chars(text)
        return text

    # -- individual steps (each independently exercisable) ------------------

    @staticmethod
    def _normalize_form(text: str, config: StageConfig) -> str:
        form = config.params.get(PARAM_UNICODE_FORM, DEFAULT_UNICODE_FORM)
        if form in _VALID_UNICODE_FORMS:
            return unicodedata.normalize(form, text)
        return text

    @staticmethod
    def _normalize_line_endings(text: str) -> str:
        if "\r" in text:
            text = text.replace("\r\n", "\n")
        return text.translate(_LINEBREAK_TABLE)

    def _handle_emoji(self, text: str, config: StageConfig) -> str:
        mode = config.params.get(PARAM_EMOJI_MODE, DEFAULT_EMOJI_MODE)
        if mode == EMOJI_MODE_VERBALIZE:
            names = self._emoji_names(config)
            return _EMOJI_RE.sub(
                lambda m: _verbalize_emoji(m.group(0), names), text
            )
        # Any unrecognized mode falls back to the safe default: removal.
        return _EMOJI_RE.sub("", text)

    @staticmethod
    def _emoji_names(config: StageConfig) -> Mapping[str, str]:
        namespace = config.language_data.get(LANGUAGE_DATA_NAMESPACE, {})
        if isinstance(namespace, Mapping):
            table = namespace.get(EMOJI_NAMES_KEY, {})
            if isinstance(table, Mapping):
                return table
        return {}

    @staticmethod
    def _normalize_punctuation(text: str, config: StageConfig) -> str:
        replacement = config.params.get(
            PARAM_DASH_REPLACEMENT, DEFAULT_DASH_REPLACEMENT
        )
        table = dict(_QUOTE_TABLE)
        for ordinal in _DASH_ORDINALS:
            table[ordinal] = replacement
        return text.translate(table)

    @staticmethod
    def _filter_chars(text: str) -> str:
        """Remove disallowed code points; map space variants/tabs to a space.

        ``unicodedata.category`` is consulted only for the *distinct*
        characters present, then a single C-level ``str.translate`` rewrites the
        whole string — keeping the pass fast on large inputs
        (``REQ-PERF-preprocessing-overhead``).
        """
        table: dict[int, str | None] = {}
        for ch in set(text):
            if ch == "\n":
                continue  # structural; preserved for layout repair
            if ch == "\t":
                table[ord(ch)] = " "  # horizontal whitespace variant
                continue
            category = unicodedata.category(ch)
            if category == "Zs" and ch != " ":
                table[ord(ch)] = " "  # NBSP and other space separators
            elif category in ("Cc", "Cf", "Cs", "Co"):
                table[ord(ch)] = None  # control / format / surrogate / private
        return text.translate(table) if table else text


def _verbalize_emoji(sequence: str, names: Mapping[str, str]) -> str:
    """Replace an emoji match with its spoken description, space-padded.

    Each code point is named from the language table, falling back to the
    Unicode character name.  Joiners and variation selectors are skipped.
    Spacing is left for the layout-repair stage to tidy.
    """
    words: list[str] = []
    for ch in sequence:
        if ch in _EMOJI_JOINERS:
            continue
        name = names.get(ch)
        if not name:
            unicode_name = unicodedata.name(ch, "")
            name = unicode_name.lower()
        if name:
            words.append(name)
    return f" {' '.join(words)} " if words else " "
