# US-synthesize-text-input: Synthesize Speech from Text Input Field

**As a** end user, **I want** to type or paste text into a field in the web UI and hear it synthesized, **so that** I can quickly test voices and models without creating an audiobook from a file.

**Status**: Approved

**Priority**: Should-have

**Source stakeholder**: [STK-end-user](../stakeholders.md)

**Related goal**: [GOAL-quick-tts-preview](../goals/GOAL-quick-tts-preview.md), [GOAL-local-tts-synthesis](../goals/GOAL-local-tts-synthesis.md), [GOAL-browser-ui](../goals/GOAL-browser-ui.md)

## Acceptance Criteria

- Given text entered in the input field, when I trigger synthesis, then MP3 audio is generated locally and plays in the browser
- Given no text is entered, when I trigger synthesis, then I see a validation message
- Given synthesis is in progress, then the UI shows a loading or progress indicator
- Given a preview synthesis has completed, then the audio is not saved to the audiobook library
- Given a preview synthesis has completed, when I navigate away or start a new preview, then the previous audio is no longer accessible

## Derived Requirements

- [REQ-F-text-preview](../requirements/REQ-F-text-preview.md) — Ephemeral TTS preview from text input
