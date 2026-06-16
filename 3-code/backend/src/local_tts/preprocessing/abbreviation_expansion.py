"""Abbreviation expansion stage — the fourth preprocessing stage.

Verbalizes common abbreviations and acronyms into their full spoken form
appropriate to the output language (``REQ-F-abbreviation-expansion``); the last
stage of the default pipeline, running after numeric/symbolic verbalization
(``DEC-text-preprocessing-pipeline``).  The stage applies, in order:

1. An optional **domain dictionary** — an acronym/technical-term → spoken-form
   mapping supplied by the caller through :class:`StageConfig` (loaded from an
   on-disk file by the service).  It is user-curated, so it takes precedence
   and is matched **case-sensitively** by default (an acronym such as ``AI``
   must not collide with the Italian word ``ai``).  Its absence must never
   break preprocessing — an empty mapping is simply skipped.
2. A language-specific **built-in abbreviation set** selected by output
   language (Italian by default, ``DEC-default-italian-language``), matched
   **case-insensitively** by default so a sentence-initial ``Es.`` expands like
   ``es.``.

Both tables arrive through the resolved :class:`StageConfig`: the built-in set
via ``language_data`` (exposed for the default language as
:data:`BUILTIN_LANGUAGE_DATA`), the domain dictionary via ``domain_dictionary``;
behaviour switches arrive through the model profile's ``params`` via ``PARAM_*``
constants (``DEC-text-preprocessing-pipeline``).  No language- or model-specific
rule is hardcoded into the shared :meth:`AbbreviationExpansionStage.run` logic —
the built-in set is a no-op for a language with no registered data, yet a
supplied domain dictionary still applies regardless of language.

The built-in set is deliberately **conservative** and refined through testing
(``REQ-F-abbreviation-expansion``): ambiguous single-letter abbreviations
(``n.``, ``v.``) are omitted to avoid mangling initials, and only entries with
an unambiguous spoken expansion are included.  An abbreviation's trailing period
is consumed by the match and dropped from the expansion (so ``il sig. Rossi`` →
``il signor Rossi``, not ``il signor. Rossi``); a period is re-appended only when
the match is followed by end-of-text or a line break — the one context where the
period unambiguously closes a sentence rather than marking a title.  A following
capital letter is **not** used as a signal, because it cannot be told apart from
a proper name after an honorific.
"""

from __future__ import annotations

import re
from typing import Any, Mapping

from local_tts.preprocessing.stages import (
    STAGE_ABBREVIATION_EXPANSION,
    StageConfig,
)

# Namespace this stage owns within a language profile's ``data`` mapping.  Each
# stage reads only its own namespace so several stages can contribute to the
# same language without colliding (see ``profiles.register_language_data``).
LANGUAGE_DATA_NAMESPACE = STAGE_ABBREVIATION_EXPANSION

# Key, inside this stage's language-data namespace, of the abbreviation table:
# a mapping of abbreviation (as written, including dots) -> spoken expansion.
ABBREVIATIONS_KEY = "abbreviations"

# --- Model-profile parameter names and defaults. ---------------------------
# Each concern can be toggled by a model profile without touching shared logic;
# every behaviour defaults to the value that makes the stage do its job.
PARAM_EXPAND_ABBREVIATIONS = "expand_abbreviations"
PARAM_APPLY_DOMAIN_DICTIONARY = "apply_domain_dictionary"
# Built-in abbreviations are lowercase tokens; matching them case-insensitively
# catches sentence-initial capitalization.  Domain entries are acronyms, which
# are case-distinguishing, so they match case-sensitively by default.
PARAM_ABBREVIATION_CASE_INSENSITIVE = "abbreviation_case_insensitive"
PARAM_DOMAIN_CASE_INSENSITIVE = "domain_case_insensitive"

# Horizontal whitespace (everything but the newline that delimits paragraphs),
# used by the final tidy pass — mirrors the numeric stage so paragraph
# boundaries established by layout repair are preserved.
_HWS_RUN_RE = re.compile(r"[^\S\n]+")
_HWS_AROUND_NL_RE = re.compile(r"[^\S\n]*\n[^\S\n]*")

# After an expanded abbreviation whose match ended in a period, this decides
# whether that period also closed a sentence: only end-of-text or a line break
# (after optional horizontal spaces) qualifies.  A following capital letter is
# deliberately not a signal — it cannot be distinguished from a proper name
# after an honorific (``sig. Rossi``).
_SENTENCE_END_AFTER_RE = re.compile(r"[^\S\n]*(?:\n|$)")


# Italian built-in abbreviation set (``DEC-default-italian-language``).  This is
# data carried by the language profile, not logic — adding a language means
# adding a table here, never editing the stage (``DEC-text-preprocessing-
# pipeline``).  Keys are written with their dots; expansions are lowercase.
BUILTIN_LANGUAGE_DATA: dict[str, dict[str, Any]] = {
    "it": {
        LANGUAGE_DATA_NAMESPACE: {
            ABBREVIATIONS_KEY: {
                # Examples / enumerations (covers REQ-F-abbreviation-expansion's
                # minimum list: es., ecc., etc., e.g., ex.).
                "ecc.": "eccetera",
                "etc.": "eccetera",
                "es.": "esempio",
                "ex.": "esempio",
                "e.g.": "per esempio",
                "i.e.": "cioè",
                "p.es.": "per esempio",
                "cfr.": "confronta",
                "cca.": "circa",
                "ca.": "circa",
                # Document references.
                "pag.": "pagina",
                "pagg.": "pagine",
                "vol.": "volume",
                "cap.": "capitolo",
                "art.": "articolo",
                "fig.": "figura",
                "tab.": "tabella",
                "n.b.": "nota bene",
                "p.s.": "post scriptum",
                # Honorifics / titles.
                "sig.": "signor",
                "sig.ra": "signora",
                "sig.na": "signorina",
                "dott.": "dottor",
                "dott.ssa": "dottoressa",
                "prof.": "professor",
                "prof.ssa": "professoressa",
                "avv.": "avvocato",
                "ing.": "ingegner",
                "arch.": "architetto",
                "geom.": "geometra",
                "rag.": "ragionier",
                "egr.": "egregio",
                "gent.": "gentile",
                "spett.": "spettabile",
                # Contact / misc.
                "tel.": "telefono",
                "cell.": "cellulare",
                # Dates / eras.
                "a.c.": "avanti Cristo",
                "d.c.": "dopo Cristo",
            }
        }
    }
}


class AbbreviationExpansionStage:
    """Expands abbreviations and acronyms before synthesis.

    Stateless and shared across requests; all per-request variation (language
    data, domain dictionary, model parameters) arrives through
    :class:`StageConfig`.
    """

    name = STAGE_ABBREVIATION_EXPANSION

    def run(self, text: str, config: StageConfig) -> str:
        if not text:
            return text

        params = config.params

        # Domain dictionary first: user-curated entries take precedence and are
        # language-independent, so they apply even when no built-in set exists.
        if params.get(PARAM_APPLY_DOMAIN_DICTIONARY, True):
            text = self._apply_domain_dictionary(text, config)

        if params.get(PARAM_EXPAND_ABBREVIATIONS, True):
            text = self._expand_builtin(text, config)

        return _tidy_spaces(text)

    # -- individual passes (each independently exercisable) -----------------

    @staticmethod
    def _apply_domain_dictionary(text: str, config: StageConfig) -> str:
        mapping = config.domain_dictionary
        if not isinstance(mapping, Mapping) or not mapping:
            return text
        case_insensitive = config.params.get(PARAM_DOMAIN_CASE_INSENSITIVE, False)
        pattern = _build_pattern(mapping, case_insensitive)
        if pattern is None:
            return text
        lookup = _lookup_factory(mapping, case_insensitive)
        return pattern.sub(lambda m: lookup(m.group(0)), text)

    @staticmethod
    def _expand_builtin(text: str, config: StageConfig) -> str:
        namespace = config.language_data.get(LANGUAGE_DATA_NAMESPACE)
        if not isinstance(namespace, Mapping):
            return text
        table = namespace.get(ABBREVIATIONS_KEY)
        if not isinstance(table, Mapping) or not table:
            return text
        case_insensitive = config.params.get(
            PARAM_ABBREVIATION_CASE_INSENSITIVE, True
        )
        pattern = _build_pattern(table, case_insensitive)
        if pattern is None:
            return text
        lookup = _lookup_factory(table, case_insensitive)

        def repl(m: re.Match[str]) -> str:
            matched = m.group(0)
            expansion = lookup(matched)
            if expansion is None:
                return matched
            # A trailing period that also closes a sentence is re-added so the
            # synthesizer still pauses (the match consumed the period).
            if matched.endswith(".") and _SENTENCE_END_AFTER_RE.match(
                text, m.end()
            ):
                return expansion + "."
            return expansion

        return pattern.sub(repl, text)


# ---------------------------------------------------------------------------
# Module-level helpers (pure; no language branching)
# ---------------------------------------------------------------------------


def _build_pattern(
    keys: Mapping[str, Any], case_insensitive: bool
) -> re.Pattern[str] | None:
    """Compile an alternation matching any key as a whole token.

    Keys are ordered longest-first so a longer abbreviation (``p.es.``) is
    preferred over a prefix of it (``es.``) at the same position.  Each
    alternative carries its own trailing boundary so a key ending in an
    alphanumeric (an acronym) is not matched inside a larger word, while a key
    ending in ``.`` needs none.  A single leading ``(?<!\\w)`` keeps matches
    from starting mid-word.  Returns ``None`` for an empty key set.
    """
    alternatives: list[str] = []
    for key in sorted(keys, key=len, reverse=True):
        if not key:
            continue
        escaped = re.escape(key)
        if key[-1].isalnum():
            escaped += r"(?!\w)"
        alternatives.append(escaped)
    if not alternatives:
        return None
    flags = re.IGNORECASE if case_insensitive else 0
    return re.compile(r"(?<!\w)(?:" + "|".join(alternatives) + ")", flags)


def _lookup_factory(mapping: Mapping[str, Any], case_insensitive: bool):
    """Build a function resolving a matched token to its expansion (or ``None``).

    For case-insensitive matching the lookup is keyed by lowercased token so the
    matched casing does not have to equal the table's.
    """
    if case_insensitive:
        lowered = {k.lower(): str(v) for k, v in mapping.items()}

        def lookup(token: str) -> str | None:
            return lowered.get(token.lower())

    else:
        exact = {k: str(v) for k, v in mapping.items()}

        def lookup(token: str) -> str | None:
            return exact.get(token)

    return lookup


def _tidy_spaces(text: str) -> str:
    """Collapse horizontal whitespace runs without disturbing newlines.

    Expansions can leave a double space (e.g. an empty domain-dictionary
    value), so a final tidy keeps the output clean while preserving the
    paragraph boundaries (blank lines) the layout-repair stage established.
    """
    text = _HWS_RUN_RE.sub(" ", text)
    text = _HWS_AROUND_NL_RE.sub("\n", text)
    return text.strip(" ")
