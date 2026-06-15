# REQ-F-abbreviation-expansion: Expand Abbreviations and Acronyms

**Type**: Functional

**Status**: Approved

**Priority**: Should-have

**Source**: [US-clean-text-for-tts](../user-stories/US-clean-text-for-tts.md)

**Source stakeholder**: [STK-end-user](../stakeholders.md)

## Description

Before synthesis, the system shall verbalize common abbreviations and acronyms into their full spoken form appropriate to the output language. This covers, at minimum:

- Common abbreviations (e.g. `es.`, `ecc.`, `etc.`, `e.g.`, `ex.`)
- A built-in, language-specific abbreviation set selected by output language

Additionally, the system shall support an **optional domain dictionary** that maps acronyms and technical terms to their intended spoken form. When supplied, dictionary entries are applied during preprocessing; when absent, preprocessing proceeds with the built-in defaults. The dictionary format and its delivery mechanism are deferred to the design phase.

## Acceptance Criteria

- Given text containing an abbreviation such as `ecc.` or `etc.`, when synthesized, then it is read as its full spoken word in the output language
- Given Italian as the output language, when common Italian abbreviations are present, then they are verbalized following Italian conventions
- Given an optional domain dictionary mapping an acronym or technical term to a spoken form, when the dictionary is supplied, then matching tokens are verbalized accordingly
- Given no domain dictionary is supplied, when text is preprocessed, then synthesis still completes using the built-in abbreviation set

## Related Requirements

- [REQ-MNT-preprocessing-pipeline](REQ-MNT-preprocessing-pipeline.md) — the abbreviation set and domain dictionary are language- and model-aware pipeline configuration

## Related Decisions

- [DEC-default-italian-language](../../2-design/decisions/DEC-default-italian-language.md) — default abbreviation set targets Italian
