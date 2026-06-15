# US-extensible-text-preprocessing: Modular, Language- and Model-Aware Preprocessing

**As a** developer, **I want** the text-preprocessing pipeline organized as modular, language- and model-aware stages with an optional domain dictionary, **so that** I can tune or extend cleaning rules per language and per TTS model without rewriting the synthesis logic.

**Status**: Approved

**Priority**: Should-have

**Source stakeholder**: [STK-developer](../stakeholders.md)

**Related goal**: [GOAL-text-normalization](../goals/GOAL-text-normalization.md)

## Acceptance Criteria

- Given the preprocessing pipeline, when I inspect it, then it is composed of discrete, independently testable stages rather than a single monolithic function
- Given a target output language, when text is preprocessed, then language-specific rules (number/date verbalization, abbreviations) are selected for that language
- Given different TTS models with different input expectations, when text is preprocessed, then the pipeline can apply model-specific configuration without changing shared cleaning logic
- Given an optional domain dictionary of acronyms and technical terms, when it is supplied, then those entries are applied during preprocessing; when it is absent, then preprocessing still runs with sensible defaults

## Derived Requirements

- [REQ-MNT-preprocessing-pipeline](../requirements/REQ-MNT-preprocessing-pipeline.md) — Modular, configurable preprocessing pipeline
- [REQ-F-abbreviation-expansion](../requirements/REQ-F-abbreviation-expansion.md) — Optional domain dictionary support
