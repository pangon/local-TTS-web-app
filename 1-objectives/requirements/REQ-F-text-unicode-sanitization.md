# REQ-F-text-unicode-sanitization: Sanitize Unicode, Spacing, Dashes, and Emoji

**Type**: Functional

**Status**: Approved

**Priority**: Must-have

**Source**: [US-clean-text-for-tts](../user-stories/US-clean-text-for-tts.md)

**Source stakeholder**: [STK-end-user](../stakeholders.md)

## Description

Before synthesis, the system shall sanitize character-level anomalies that would otherwise corrupt or degrade the audio. This covers, at minimum:

- Removal of invisible / zero-width characters (e.g. zero-width space, soft hyphen, BOM, control characters)
- Conversion of non-breaking spaces and other whitespace variants to normal spaces
- Normalization of dash variants (em dash, en dash, figure dash) to a consistent form
- Normalization of smart/typographic quotes and other punctuation variants to standard equivalents
- Removal of disallowed or unsupported Unicode characters
- Emoji either removed or verbalized to a descriptive word, per configuration

The exact character classes and mapping tables are deferred to the design phase and refined through testing.

## Acceptance Criteria

- Given text containing zero-width spaces, soft hyphens, or control characters, when it is preprocessed, then those characters are removed and do not appear in the synthesized audio
- Given text containing non-breaking spaces, when it is preprocessed, then they are converted to normal spaces
- Given text mixing em dashes, en dashes, and hyphens, when it is preprocessed, then dash usage is normalized to a consistent form
- Given text containing smart quotes, when it is preprocessed, then they are normalized to standard quotes
- Given text containing emoji, when it is preprocessed, then each emoji is either removed or replaced by a spoken word according to the configured behavior

## Related Assumptions

- [ASM-input-text-quality-varies](../assumptions/ASM-input-text-quality-varies.md) — real-world inputs contain non-standard Unicode and inconsistent punctuation
