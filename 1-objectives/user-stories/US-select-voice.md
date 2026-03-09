# US-select-voice: Select Voice and Language

**As a** end user, **I want** to select a voice and output language before generating an audiobook, **so that** the result sounds natural and matches the language of my text.

**Status**: Draft

**Priority**: Should-have

**Source stakeholder**: [STK-end-user](../stakeholders.md)

**Related goal**: [GOAL-audio-quality](../goals/GOAL-audio-quality.md)

## Acceptance Criteria

- Given available voices for the loaded model, when I open the audiobook creation form, then I see a list of voices I can choose from
- Given a selected voice, when I trigger synthesis, then the audio is generated using that voice
- Given languages supported by the chosen model, when I open the creation form, then I can select the output language
- Given no explicit selection, when I trigger synthesis, then a sensible default voice and language are used

## Derived Requirements

- [REQ-F-voice-language-selection](../requirements/REQ-F-voice-language-selection.md) — Select voice and language before synthesis
