# REQ-F-text-numeric-symbolic-verbalization: Verbalize Numbers, Dates, and Symbols

**Type**: Functional

**Status**: Approved

**Priority**: Must-have

**Source**: [US-clean-text-for-tts](../user-stories/US-clean-text-for-tts.md)

**Source stakeholder**: [STK-end-user](../stakeholders.md)

## Description

Before synthesis, the system shall transcribe numeric and symbolic content into spelled-out words appropriate to the output language. This covers, at minimum:

- Cardinal and ordinal numbers (including thousands separators and decimals)
- Dates written in full (day, month, year)
- Percentages (`%`) and common currency symbols
- Other common symbols read as words where applicable (e.g. `&`, `+`, `=`, `°`)

Verbalization rules are language-dependent and selected based on the output language (see [REQ-MNT-preprocessing-pipeline](REQ-MNT-preprocessing-pipeline.md)). The exact symbol coverage and verbalization tables are deferred to the design phase and refined through testing.

## Acceptance Criteria

- Given text containing a number such as `1.234,56` (or `1,234.56`), when synthesized in the configured language, then it is read as the full spoken number rather than digit-by-digit or skipped
- Given a date such as `15/03/2026`, when synthesized, then it is read in full (e.g. "fifteen March twenty twenty-six" in the appropriate language)
- Given a percentage `25%` or a currency amount `€10`, when synthesized, then the symbol is read as its spoken word in the output language
- Given Italian as the default output language, when numeric or symbolic content is verbalized, then the spoken form follows Italian conventions

## Related Decisions

- [DEC-default-italian-language](../../2-design/decisions/DEC-default-italian-language.md) — Italian is the default output language, so default verbalization rules target Italian

## Related Assumptions

- [ASM-input-text-quality-varies](../assumptions/ASM-input-text-quality-varies.md) — raw inputs routinely contain unverbalized numerals and symbols
