# REQ-MNT-preprocessing-pipeline: Modular, Configurable Preprocessing Pipeline

**Type**: Maintainability

**Status**: Approved

**Priority**: Should-have

**Source**: [US-extensible-text-preprocessing](../user-stories/US-extensible-text-preprocessing.md)

**Source stakeholder**: [STK-developer](../stakeholders.md)

## Description

The text-preprocessing capability shall be implemented as a modular pipeline of discrete, independently testable stages, rather than a single monolithic function. The pipeline shall be configurable along two axes:

- **Per output language** — language-specific stages (number/date verbalization, abbreviation sets) are selected based on the configured output language
- **Per TTS model** — the pipeline can apply model-specific configuration (which stages run, and their parameters) to accommodate differing input expectations of different TTS models, without modifying shared cleaning logic

This requirement governs the structure of the preprocessing capability; the individual cleaning behaviors are specified by the functional requirements it supports. It aligns with [REQ-MNT-modular-ai-layer](REQ-MNT-modular-ai-layer.md) and the model-adapter pattern.

## Acceptance Criteria

- Given the preprocessing implementation, when inspected, then it is decomposed into discrete stages that can be unit-tested in isolation
- Given a configured output language, when text is preprocessed, then the language-appropriate stages are selected
- Given two different TTS models, when each is selected, then model-specific preprocessing configuration is applied without changing the shared stage implementations
- Given a new language or model needs different rules, when it is added, then it can be introduced by configuration/new stage rather than by editing existing shared logic

## Related Requirements

- [REQ-MNT-modular-ai-layer](REQ-MNT-modular-ai-layer.md) — consistent modularity/extensibility approach for the AI layer
- [REQ-F-text-numeric-symbolic-verbalization](REQ-F-text-numeric-symbolic-verbalization.md), [REQ-F-abbreviation-expansion](REQ-F-abbreviation-expansion.md) — language-specific behaviors configured through this pipeline
