# GOAL-text-normalization: Normalize and Clean Input Text into TTS-Ready Form

**Description**: Transform raw input text into a clean, TTS-ready form before synthesis, so that the generated audio correctly verbalizes numbers, dates, and symbols, is free of artifacts (invisible characters, stray page numbers, broken line wraps, emoji), and preserves the intended sentence structure. Testing of the audiobook pipeline revealed that real-world inputs — particularly text extracted from PDFs — require substantially more preprocessing than the simple chapter-detection heuristic originally assumed. This goal makes text normalization a first-class capability that feeds both audiobook creation and the quick text preview.

**Status**: Approved

**Priority**: Must-have

**Source stakeholder**: [STK-end-user](../stakeholders.md)

## Success Criteria

- [ ] Numbers, dates, percentages, currency, and other symbols are verbalized into words appropriate to the output language
- [ ] Disallowed and invisible Unicode, non-breaking spaces, emoji, and inconsistent dashes/quotes are normalized or removed
- [ ] Spurious line breaks from PDF-to-text extraction are repaired so sentences remain intact, end-of-line hyphenation is resolved, and isolated page numbers are stripped
- [ ] Common abbreviations and acronyms are verbalized; an optional domain dictionary can be applied
- [ ] The normalization pipeline is modular and can be configured per output language and per TTS model
- [ ] Audio generated from normalized text is measurably more natural than audio from raw text on representative messy inputs (e.g. a PDF-extracted document)

## Related Artifacts

- User stories: [US-clean-text-for-tts](../user-stories/US-clean-text-for-tts.md), [US-extensible-text-preprocessing](../user-stories/US-extensible-text-preprocessing.md)
- Requirements: [REQ-F-text-numeric-symbolic-verbalization](../requirements/REQ-F-text-numeric-symbolic-verbalization.md), [REQ-F-text-unicode-sanitization](../requirements/REQ-F-text-unicode-sanitization.md), [REQ-F-text-layout-repair](../requirements/REQ-F-text-layout-repair.md), [REQ-F-abbreviation-expansion](../requirements/REQ-F-abbreviation-expansion.md), [REQ-MNT-preprocessing-pipeline](../requirements/REQ-MNT-preprocessing-pipeline.md)
- Supports: [GOAL-audio-quality](GOAL-audio-quality.md), [GOAL-audiobook-creation](GOAL-audiobook-creation.md)
- Assumptions: [ASM-input-text-quality-varies](../assumptions/ASM-input-text-quality-varies.md)
