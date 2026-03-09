# REQ-F-default-voice-quality: Default Voice Quality Assurance

**Type**: Functional

**Status**: Approved

**Priority**: Should-have

**Source**: [US-select-voice](../user-stories/US-select-voice.md), [GOAL-audio-quality](../goals/GOAL-audio-quality.md)

**Source stakeholder**: [STK-end-user](../stakeholders.md)

## Description

The application must ship with a documented default model/voice combination that produces intelligible, natural-sounding speech. The default language is Italian. The default is pre-tested during development so that first-time users get a good experience without manual configuration.

## Acceptance Criteria

- Given a loaded model with no explicit voice selection, when the user triggers synthesis, then the system uses a pre-tested default voice for that model with Italian as the default language
- Given the default voice and language, when synthesizing Italian text, then a native speaker can understand ≥ 95% of words on first listen (validated by developer listening test during development)
- Given the project documentation, then at least one model/voice/language combination is documented as the recommended default with a sample audio file

## Related Assumptions

- [ASM-huggingface-models-available](../assumptions/ASM-huggingface-models-available.md) — viable models with acceptable quality and Italian language support must exist
