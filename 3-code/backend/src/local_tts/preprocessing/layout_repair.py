"""Layout-repair stage — the second preprocessing stage.

Repairs layout artifacts introduced by document conversion — above all
PDF-to-text extraction — so text is segmented into the sentences and paragraphs
the author intended (``REQ-F-text-layout-repair``); the second stage of the
default pipeline, running after Unicode sanitization and before chapter
detection (``DEC-text-preprocessing-pipeline``).  In order, the stage:

1. Normalizes each line's horizontal whitespace (collapsing runs of spaces/tabs
   to a single space and trimming the ends).
2. Groups lines into paragraph **blocks** delimited by blank lines, so genuine
   paragraph and chapter boundaries are never crossed when reflowing.
3. Drops isolated page-number / standalone layout fragments — a block that is
   nothing but a page number (the "surrounded by blank lines" case).
4. Reflows the soft line breaks inside each block: line fragments of one
   sentence are rejoined (with a single space), and end-of-line hyphenation is
   resolved (``exam-\\nple`` → ``example``).  Heading-like and list-item lines
   are kept on their own line so chapter detection (``REQ-F-chapter-split-output``)
   still functions and list structure survives.
5. Re-emits blocks separated by a single blank line, collapsing runs of blank
   lines to one consistent paragraph boundary.

The stage carries only **universal** structural tables (page-number, heading,
and list-item recognizers).  It has no language-specific *cleaning* data, so —
unlike :mod:`unicode_sanitization` — it exposes no ``BUILTIN_LANGUAGE_DATA``.
Behavior switches (de-hyphenation, reflow, page stripping, whitespace collapse)
read from the model profile's ``params`` via ``PARAM_*`` constants with safe
defaults — no language- or model-specific rule is hardcoded into the shared
logic (``DEC-text-preprocessing-pipeline``).

The exact heuristics are deliberately conservative and refined through testing
(``REQ-F-text-layout-repair``).  Known refinements deferred to testing: the
compound-word de-hyphenation ambiguity (``self-\\nesteem`` collapses rather than
keeping the hyphen), Roman-numeral page numbers, and wrapped list items.
"""

from __future__ import annotations

import re

from local_tts.preprocessing.stages import (
    STAGE_LAYOUT_REPAIR,
    StageConfig,
)

# --- Model-profile parameter names and defaults. ---------------------------
# Every behavior defaults to on — that is the stage's purpose — but a model
# profile can disable any of them without touching this shared logic.
PARAM_DEHYPHENATE = "dehyphenate"
DEFAULT_DEHYPHENATE = True

PARAM_REFLOW = "reflow"
DEFAULT_REFLOW = True

PARAM_STRIP_PAGE_NUMBERS = "strip_page_numbers"
DEFAULT_STRIP_PAGE_NUMBERS = True

PARAM_COLLAPSE_WHITESPACE = "collapse_whitespace"
DEFAULT_COLLAPSE_WHITESPACE = True

# --- Universal structural recognizers. -------------------------------------

# Runs of horizontal whitespace (anything whitespace except the newline that
# delimits lines).  Used to collapse intra-line whitespace to a single space.
_WS_RUN_RE = re.compile(r"[^\S\n]+")

# A letter immediately before a trailing hyphen — the end-of-line hyphenation
# signal.  Restricted to letters (not digits) so numeric ranges like "5-" are
# not treated as a split word.
_ENDS_HYPHEN_RE = re.compile(r"[^\W\d_]-$")

# A line that begins with a letter — used to confirm a de-hyphenation join
# (the continuation of a split word starts with a letter).
_STARTS_LETTER_RE = re.compile(r"[^\W\d_]")

# An isolated page number / bare layout fragment: an optional "page"/"pag."
# word and bracket/dash decorations around 1–4 digits, nothing else.  Dash
# variants are already normalized to "-" by the Unicode stage; the extra
# variants here keep the stage correct when exercised in isolation.
_PAGE_NUMBER_RE = re.compile(
    r"^[\[\(\-–—\s]*"
    r"(?:p(?:ag|age|agina)?\.?\s*)?"
    r"\d{1,4}"
    r"[\s\]\).\-–—]*$",
    re.IGNORECASE,
)

# Heading-like line openers.  Aligned with the Chapter Parser's keywords so
# reflow never glues a chapter/part heading onto the following text and defeats
# chapter detection (``REQ-F-chapter-split-output``); the Italian forms are
# included for the default language (``DEC-default-italian-language``).  This is
# a universal default vocabulary table, refined through testing — not logic
# that branches on the configured language.
_HEADING_RE = re.compile(
    r"^(?:chapter|part|capitolo|parte|prologo|prologue|epilogo|epilogue)\b",
    re.IGNORECASE,
)

# A list-item line: a bullet or an enumerator followed by whitespace.  Such
# lines are kept on their own line so list structure is not collapsed into a
# run of text.
_LIST_ITEM_RE = re.compile(
    r"^(?:[-*•‣◦·]\s+|\d{1,3}[.)]\s+)"
)


class LayoutRepairStage:
    """Repairs document-conversion layout artifacts before synthesis.

    Stateless and shared across requests; all per-request variation
    (model profile parameters) arrives through :class:`StageConfig`.
    """

    name = STAGE_LAYOUT_REPAIR

    def run(self, text: str, config: StageConfig) -> str:
        if not text:
            return text

        params = config.params
        dehyphenate = params.get(PARAM_DEHYPHENATE, DEFAULT_DEHYPHENATE)
        reflow = params.get(PARAM_REFLOW, DEFAULT_REFLOW)
        strip_pages = params.get(
            PARAM_STRIP_PAGE_NUMBERS, DEFAULT_STRIP_PAGE_NUMBERS
        )
        collapse_ws = params.get(
            PARAM_COLLAPSE_WHITESPACE, DEFAULT_COLLAPSE_WHITESPACE
        )

        lines = self._normalize_lines(text, collapse_ws)
        blocks = self._split_blocks(lines)

        paragraphs: list[str] = []
        for block in blocks:
            if strip_pages and self._is_page_number_block(block):
                continue
            paragraph = self._repair_block(block, dehyphenate, reflow)
            if paragraph:
                paragraphs.append(paragraph)

        return "\n\n".join(paragraphs)

    # -- individual steps (each independently exercisable) ------------------

    @staticmethod
    def _normalize_lines(text: str, collapse_ws: bool) -> list[str]:
        """Split into lines, collapsing/trimming each line's whitespace.

        Line endings are normalized defensively so the stage behaves the same
        whether or not the Unicode stage ran first.
        """
        text = text.replace("\r\n", "\n").replace("\r", "\n")
        lines = text.split("\n")
        if not collapse_ws:
            return lines
        return [_WS_RUN_RE.sub(" ", line).strip() for line in lines]

    @staticmethod
    def _split_blocks(lines: list[str]) -> list[list[str]]:
        """Group non-blank lines into blocks delimited by blank lines."""
        blocks: list[list[str]] = []
        current: list[str] = []
        for line in lines:
            if line.strip():
                current.append(line)
            elif current:
                blocks.append(current)
                current = []
        if current:
            blocks.append(current)
        return blocks

    @staticmethod
    def _is_page_number_block(block: list[str]) -> bool:
        """Whether *block* is a single isolated page-number/fragment line."""
        return len(block) == 1 and bool(_PAGE_NUMBER_RE.match(block[0].strip()))

    @staticmethod
    def _repair_block(
        block: list[str], dehyphenate: bool, reflow: bool
    ) -> str:
        """Reflow one block into a single paragraph string.

        Heading and list-item lines are kept on their own physical line (so
        chapter detection and list structure survive); the remaining prose
        lines are rejoined into one line, resolving end-of-line hyphenation.
        When reflow is disabled the lines are preserved as-is.
        """
        if not reflow:
            return "\n".join(block)

        physical: list[str] = []
        buffer = ""

        for line in block:
            line = line.strip()
            if _HEADING_RE.match(line) or _LIST_ITEM_RE.match(line):
                if buffer:
                    physical.append(buffer)
                    buffer = ""
                physical.append(line)
                continue

            if not buffer:
                buffer = line
            elif (
                dehyphenate
                and _ENDS_HYPHEN_RE.search(buffer)
                and _STARTS_LETTER_RE.match(line)
            ):
                buffer = buffer[:-1] + line
            else:
                buffer = f"{buffer} {line}"

        if buffer:
            physical.append(buffer)

        return "\n".join(physical)
