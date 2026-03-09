# REQ-F-voice-language-selection: Select Voice and Language Before Synthesis

**Type**: Functional

**Status**: Draft

**Priority**: Should-have

**Source**: [US-select-voice](../user-stories/US-select-voice.md)

**Source stakeholder**: [STK-end-user](../stakeholders.md)

## Description

The system shall display the available voices and languages for the currently loaded model. The user can select a voice and output language before triggering synthesis. When no explicit selection is made, sensible defaults are used.

## Acceptance Criteria

- Given a loaded TTS model with multiple voices, when the user opens the audiobook creation form, then a list of available voices is displayed
- Given a selected voice, when the user triggers synthesis, then the audio is generated using that voice
- Given a loaded model supporting multiple languages, when the user opens the creation form, then available languages are listed for selection
- Given no explicit voice or language selection, when the user triggers synthesis, then sensible defaults are used
