# REQ-F-playback-resume: Persist and Resume Playback Position

**Type**: Functional

**Status**: Approved

**Priority**: Must-have

**Source**: [US-play-audiobook](../user-stories/US-play-audiobook.md)

**Source stakeholder**: [STK-end-user](../stakeholders.md)

## Description

The system shall persist playback position at two levels: (1) an audiobook-level bookmark recording which chapter the user was last listening to, and (2) a per-chapter bookmark recording the timestamp within each individual chapter. When the user returns to an audiobook, playback resumes from the last active chapter at its saved position. When the user navigates to a previously listened chapter, playback resumes from that chapter's saved position.

## Acceptance Criteria

- Given the user stops playback, then the current chapter is recorded as the audiobook-level bookmark and the current timestamp is recorded as that chapter's bookmark
- Given the user returns to a previously played audiobook, when they start playback, then it loads the last active chapter and resumes from that chapter's saved position
- Given the user navigates to a chapter they have previously listened to, then playback resumes from that chapter's saved position
- Given the user navigates to a chapter they have never listened to, then playback begins from the start
- Given the user has never played an audiobook, when they start playback, then it begins from the start of the first chapter
