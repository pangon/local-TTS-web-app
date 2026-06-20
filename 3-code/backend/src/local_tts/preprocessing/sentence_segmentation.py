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

The split mirrors the synthesizer's own sentence chunking (split on
``.``/``!``/``?`` followed by whitespace), so the one-line-per-sentence preview
matches the TTS segmentation.  Existing newlines are preserved: blank lines keep
paragraph boundaries, and standalone structural lines (headings, list items,
bare numbers) — already on their own physical line from layout repair — are left
untouched because they contain no intra-line sentence break.

The stage carries only **universal** structural logic (sentence terminators are
language-independent here), so — like :mod:`layout_repair` — it exposes no
``BUILTIN_LANGUAGE_DATA``.  Its single behavior switch reads from the model
profile's ``params`` via the ``PARAM_*`` constant with a safe default
(``DEC-text-preprocessing-pipeline``).
"""

from __future__ import annotations

import re

from local_tts.preprocessing.stages import (
    STAGE_SENTENCE_SEGMENTATION,
    StageConfig,
)

# --- Model-profile parameter name and default. ----------------------------
PARAM_SEGMENT_SENTENCES = "segment_sentences"
DEFAULT_SEGMENT_SENTENCES = True

# Split on sentence-ending punctuation (. ! ?) followed by whitespace. This
# mirrors the synthesizer's `split_into_sentences` so the reviewed text is
# segmented exactly like the TTS chunks. A lookbehind keeps the terminator on
# the preceding sentence; only intra-line whitespace runs (typically a single
# space) become line breaks here, because the stage processes one physical
# line at a time.
_SENTENCE_BREAK_RE = re.compile(r"(?<=[.!?])\s+")


class SentenceSegmentationStage:
    """Splits each line into one sentence per line.

    Stateless and shared across requests; the per-request behavior switch
    arrives through :class:`StageConfig`.
    """

    name = STAGE_SENTENCE_SEGMENTATION

    def run(self, text: str, config: StageConfig) -> str:
        if not text:
            return text

        if not config.params.get(
            PARAM_SEGMENT_SENTENCES, DEFAULT_SEGMENT_SENTENCES
        ):
            return text

        out: list[str] = []
        for line in text.split("\n"):
            stripped = line.strip()
            if not stripped:
                # Preserve blank lines so paragraph boundaries survive.
                out.append("")
                continue
            for sentence in _SENTENCE_BREAK_RE.split(stripped):
                sentence = sentence.strip()
                if sentence:
                    out.append(sentence)

        return "\n".join(out)
