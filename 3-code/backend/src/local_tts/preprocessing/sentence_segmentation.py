"""Sentence-segmentation stage — the final preprocessing stage.

Puts each sentence on its own line so the reviewed, TTS-ready text is segmented
into the sentences the author intended (``REQ-F-text-layout-repair``) and the
normalized text the user reviews (``REQ-USA-normalized-text-review``) mirrors
the chunks the synthesizer will actually speak.

Unlike layout repair (which *reflows* soft-wrapped sentence fragments back
together), this stage *splits* a line that runs several sentences together onto
one line each.  It runs **last** in the default pipeline
(``DEC-text-preprocessing-pipeline``) — after numeric/symbolic verbalization and
abbreviation expansion — so a sentence-ending period is no longer ambiguous with
a thousands separator (``11.988``) or an abbreviation dot (``E.F.``, ``sig.``):
those have already been expanded away by the time this stage runs.

The split is on ``.``/``!``/``?`` followed by whitespace.  The synthesizer
chunks the confirmed text **one line per chunk** (it splits on newlines, not
punctuation), so this stage's one-sentence-per-line output *defines* the TTS
segmentation and the reviewed text matches the spoken chunks exactly.  Existing
newlines are preserved: blank lines keep paragraph boundaries, and standalone
structural lines (headings, list items, bare numbers) — already on their own
physical line from layout repair — are left untouched because they contain no
intra-line sentence break.

The stage also performs **dialogue isolation**: a spoken span delimited by the
directional double-angle guillemets (``«`` … ``»``, left intact by the Unicode
stage) is put onto its own line(s) by introducing a line break *before* an
opening ``«`` and *after* a closing ``»`` — so the narration before a quote, the
quote itself, and any trailing dialogue tag (e.g. ``… all'atterraggio» comunicò.``)
each become distinct TTS chunks.  After using their direction for chunking the
guillemets are flattened to straight ``"`` (the convention the Unicode stage
applies to every other quote variant); this flattening is unconditional so the
output quote style is stable regardless of the behavior switches below.

The stage carries only **universal** structural logic (sentence terminators and
guillemets are language-independent here), so — like :mod:`layout_repair` — it
exposes no ``BUILTIN_LANGUAGE_DATA``.  Its behavior switches read from the model
profile's ``params`` via the ``PARAM_*`` constants with safe defaults
(``DEC-text-preprocessing-pipeline``).
"""

from __future__ import annotations

import re

from local_tts.preprocessing.stages import (
    STAGE_SENTENCE_SEGMENTATION,
    StageConfig,
)

# --- Model-profile parameter names and defaults. --------------------------
PARAM_SEGMENT_SENTENCES = "segment_sentences"
DEFAULT_SEGMENT_SENTENCES = True

PARAM_ISOLATE_QUOTES = "isolate_quotes"
DEFAULT_ISOLATE_QUOTES = True

# Split on sentence-ending punctuation (. ! ?) followed by whitespace. The
# resulting one-sentence-per-line layout becomes the TTS chunking: the
# synthesizer splits the confirmed text on newlines. A lookbehind keeps the
# terminator on the preceding sentence; only intra-line whitespace runs
# (typically a single space) become line breaks here, because the stage
# processes one physical line at a time.
_SENTENCE_BREAK_RE = re.compile(r"(?<=[.!?])\s+")

# Directional double-angle guillemets that delimit a spoken span.
_OPEN_QUOTE = "«"
_CLOSE_QUOTE = "»"


class SentenceSegmentationStage:
    """Splits each line into one sentence per line and isolates dialogue.

    Stateless and shared across requests; the per-request behavior switches
    arrive through :class:`StageConfig`.
    """

    name = STAGE_SENTENCE_SEGMENTATION

    def run(self, text: str, config: StageConfig) -> str:
        if not text:
            return text

        params = config.params
        segment = params.get(PARAM_SEGMENT_SENTENCES, DEFAULT_SEGMENT_SENTENCES)
        isolate_quotes = params.get(
            PARAM_ISOLATE_QUOTES, DEFAULT_ISOLATE_QUOTES
        )

        if isolate_quotes:
            # Break before an opening guillemet and after a closing one so the
            # spoken span lands in its own chunk(s). These breaks survive into
            # the per-line splitting below.
            text = text.replace(_OPEN_QUOTE, "\n" + _OPEN_QUOTE).replace(
                _CLOSE_QUOTE, _CLOSE_QUOTE + "\n"
            )

        if segment or isolate_quotes:
            out: list[str] = []
            for line in text.split("\n"):
                stripped = line.strip()
                if not stripped:
                    # Preserve blank lines so paragraph boundaries survive.
                    out.append("")
                    continue
                pieces = (
                    _SENTENCE_BREAK_RE.split(stripped) if segment else [stripped]
                )
                for piece in pieces:
                    piece = piece.strip()
                    if piece:
                        out.append(piece)
            text = "\n".join(out)
            # The guillemet inserts (and any adjacent paragraph break) can
            # leave runs of blank lines / leading-trailing newlines; tidy them.
            text = re.sub(r"\n{3,}", "\n\n", text).strip("\n")

        # Flatten the directional guillemets to straight quotes now that their
        # direction has been used for chunking — keeping the output quote style
        # consistent with the Unicode stage regardless of the switches above.
        return text.replace(_OPEN_QUOTE, '"').replace(_CLOSE_QUOTE, '"')
