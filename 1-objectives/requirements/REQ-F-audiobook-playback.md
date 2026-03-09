# REQ-F-audiobook-playback: Browser Audio Playback with Chapter Navigation

**Type**: Functional

**Status**: Draft

**Priority**: Must-have

**Source**: [US-play-audiobook](../user-stories/US-play-audiobook.md)

**Source stakeholder**: [STK-end-user](../stakeholders.md)

## Description

The system shall play audiobook audio in the browser. For audiobooks with multiple chapters, the player shall provide controls to navigate between chapters.

## Acceptance Criteria

- Given an audiobook in the library, when the user selects it, then audio playback starts in the browser
- Given an audiobook with multiple chapters, when playing, then the user can skip to the next or previous chapter
- Given an audiobook with a single chapter, when playing, then chapter navigation controls are not shown

## Related Assumptions

- [ASM-browser-mp3-playback](../assumptions/ASM-browser-mp3-playback.md) — assumes target browsers can natively play MP3 audio
