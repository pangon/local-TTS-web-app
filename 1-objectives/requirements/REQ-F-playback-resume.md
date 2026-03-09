# REQ-F-playback-resume: Persist and Resume Playback Position

**Type**: Functional

**Status**: Approved

**Priority**: Must-have

**Source**: [US-play-audiobook](../user-stories/US-play-audiobook.md)

**Source stakeholder**: [STK-end-user](../stakeholders.md)

## Description

The system shall persist the current playback position (chapter and timestamp). When the user returns to the same audiobook, playback shall resume from the last saved position.

## Acceptance Criteria

- Given the user stops playback of an audiobook, then the current chapter and timestamp are persisted
- Given the user returns to a previously played audiobook, when they start playback, then it resumes from the last saved position
- Given the user has never played an audiobook, when they start playback, then it begins from the start of the first chapter
