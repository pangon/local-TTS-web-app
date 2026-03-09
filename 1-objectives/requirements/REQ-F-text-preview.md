# REQ-F-text-preview: Ephemeral TTS Preview from Text Input

**Type**: Functional

**Status**: Draft

**Priority**: Should-have

**Source**: [US-synthesize-text-input](../user-stories/US-synthesize-text-input.md)

**Source stakeholder**: [STK-end-user](../stakeholders.md)

## Description

The system shall allow the user to type or paste text into a field and synthesize it locally into MP3 audio that plays in the browser. The preview audio is ephemeral — it is not saved to the library and is discarded on navigation or new preview. If no text is entered, a validation message is shown. A loading indicator is displayed during synthesis.

## Acceptance Criteria

- Given text entered in the input field, when the user triggers synthesis, then MP3 audio is generated locally and plays in the browser
- Given no text is entered, when the user triggers synthesis, then a validation message is displayed
- Given synthesis is in progress, then the UI shows a loading indicator
- Given a preview has completed, then the audio is not saved to the audiobook library
- Given a preview has completed, when the user navigates away or starts a new preview, then the previous audio is discarded

## Related Assumptions

- [ASM-browser-mp3-playback](../assumptions/ASM-browser-mp3-playback.md) — assumes target browsers can natively play MP3 audio
