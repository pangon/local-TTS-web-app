# ASM-input-text-quality-varies: Input Text Quality Varies and Needs Cleaning

**Category**: User

**Status**: Verified

**Risk if wrong**: Medium — if real-world inputs were already clean, the preprocessing effort would be largely unnecessary; if the artifacts are even more varied than assumed, the pipeline may miss cases and produce degraded audio

## Statement

Real-world input text — especially documents converted to `.txt` from PDFs — routinely contains formatting and content artifacts that degrade TTS output unless cleaned: spurious mid-sentence line breaks, end-of-line hyphenation, isolated page numbers, non-standard and invisible Unicode, inconsistent dashes and quotes, emoji, and unverbalized numbers, dates, and symbols. Users will not reliably clean these by hand before uploading.

## Rationale

Testing of the audiobook pipeline on representative inputs (including PDF-extracted text) surfaced these artifacts directly, contradicting the earlier assumption that a simple chapter-detection heuristic would suffice. PDF-to-text conversion is a common way users obtain `.txt` files and is known to introduce hard line breaks, hyphenation, and layout fragments.

## Verification Plan

Collect a representative sample of real-world inputs (a born-digital `.txt`, a PDF-extracted document, and a document containing tables/lists/symbols). Catalogue the artifact categories actually present and confirm they match the cleaning stages defined by the text-normalization requirements. Compare synthesized audio before and after normalization to confirm the artifacts materially affect output quality.

**Verified (2026-06-16)**: confirmed during the developer's own testing of the audiobook pipeline — real-world inputs (notably PDF-extracted text) exhibited the assumed artifacts and materially degraded TTS output, motivating the text-normalization capability.

## Related Artifacts

- [GOAL-text-normalization](../goals/GOAL-text-normalization.md)
- [US-clean-text-for-tts](../user-stories/US-clean-text-for-tts.md)
- [REQ-F-text-numeric-symbolic-verbalization](../requirements/REQ-F-text-numeric-symbolic-verbalization.md), [REQ-F-text-unicode-sanitization](../requirements/REQ-F-text-unicode-sanitization.md), [REQ-F-text-layout-repair](../requirements/REQ-F-text-layout-repair.md), [REQ-F-abbreviation-expansion](../requirements/REQ-F-abbreviation-expansion.md)
- Supersedes part of the scope implied by [ASM-text-file-format](ASM-text-file-format.md) (which addresses encoding/size, not content quality)
