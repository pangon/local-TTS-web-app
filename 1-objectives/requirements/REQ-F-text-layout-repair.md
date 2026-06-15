# REQ-F-text-layout-repair: Repair Layout Artifacts and Reflow Sentences

**Type**: Functional

**Status**: Approved

**Priority**: Must-have

**Source**: [US-clean-text-for-tts](../user-stories/US-clean-text-for-tts.md)

**Source stakeholder**: [STK-end-user](../stakeholders.md)

## Description

Before synthesis, the system shall repair layout artifacts introduced by document conversion (notably PDF-to-text extraction) so that text is segmented into the sentences and paragraphs the author intended. This covers, at minimum:

- Removal of spurious hard line breaks that split a single sentence across multiple lines, reflowing the text so each sentence stays intact and can be passed to the TTS model as a single chunk
- Resolution of end-of-line hyphenation (rejoining words split by a hyphen at a line break)
- Removal of isolated page numbers and other standalone layout fragments (e.g. running headers/footers reduced to a bare number)
- Normalization of list formatting and of irregular whitespace (collapsing runs of spaces/blank lines to a consistent form)

Preserving genuine paragraph and chapter boundaries is required: reflow shall not merge distinct paragraphs or defeat chapter detection ([REQ-F-chapter-split-output](REQ-F-chapter-split-output.md)). The exact detection heuristics are deferred to the design phase and refined through testing.

## Acceptance Criteria

- Given a paragraph whose sentences are broken across hard line breaks (typical of PDF extraction), when it is preprocessed, then the sentences are reflowed so each remains intact and is not split into separate TTS chunks
- Given a word hyphenated across a line break (e.g. `exam-\nple`), when it is preprocessed, then it is rejoined into the single word (`example`)
- Given a line containing only a page number surrounded by blank lines, when it is preprocessed, then the page number is removed and not synthesized
- Given irregular runs of spaces or blank lines, when it is preprocessed, then whitespace is normalized to a consistent form
- Given genuine paragraph and chapter boundaries, when reflow is applied, then those boundaries are preserved and chapter detection still functions

## Related Requirements

- [REQ-F-chapter-split-output](REQ-F-chapter-split-output.md) — layout repair composes with, and must not defeat, chapter detection

## Related Assumptions

- [ASM-input-text-quality-varies](../assumptions/ASM-input-text-quality-varies.md) — PDF-extracted inputs are the primary source of these artifacts
