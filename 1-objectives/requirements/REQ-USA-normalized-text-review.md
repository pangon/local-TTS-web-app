# REQ-USA-normalized-text-review: Review Normalized Text Before Generation

**Type**: Usability

**Status**: Approved

**Priority**: Should-have

**Source**: [US-clean-text-for-tts](../user-stories/US-clean-text-for-tts.md)

**Source stakeholder**: [STK-end-user](../stakeholders.md)

## Description

Before committing to audio generation, the system shall let the user review the normalized text — the exact text that will be sent to the TTS model after the preprocessing pipeline has run — and explicitly confirm to proceed. This gives the user a chance to catch cases where automatic cleaning altered the text in an undesired way (e.g. over-aggressive reflow of intentionally line-broken content) before spending synthesis time.

The presentation form (full normalized text, or a before/after comparison) is deferred to the design phase. Review is a confirmation step, not a mandatory manual edit: the user can proceed directly, consistent with the automatic-cleaning intent of [US-clean-text-for-tts](../user-stories/US-clean-text-for-tts.md).

## Acceptance Criteria

- Given an uploaded document has been normalized, when the user is about to start generation, then the system shows the normalized text that will be synthesized and requires an explicit action to proceed
- Given the displayed normalized text, when the user reviews it, then they can clearly tell what will be read aloud (including how numbers, dates, and symbols were verbalized)
- Given the user is satisfied, when they confirm, then synthesis proceeds using exactly the reviewed text
- Given the quick text-preview path where the input text is already visible, then the review step may be satisfied inline without a separate confirmation screen

## Related Requirements

- [REQ-F-text-numeric-symbolic-verbalization](REQ-F-text-numeric-symbolic-verbalization.md), [REQ-F-text-unicode-sanitization](REQ-F-text-unicode-sanitization.md), [REQ-F-text-layout-repair](REQ-F-text-layout-repair.md), [REQ-F-abbreviation-expansion](REQ-F-abbreviation-expansion.md) — the transformations the user reviews the result of
