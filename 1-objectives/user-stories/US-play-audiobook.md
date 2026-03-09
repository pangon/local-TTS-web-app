# US-play-audiobook: Play Audiobook with Resume

**As a** end user, **I want** to play an audiobook from the library and resume where I left off, **so that** I don't lose my place between sessions.

**Status**: Draft

**Priority**: Must-have

**Source stakeholder**: [STK-end-user](../stakeholders.md)

**Related goal**: [GOAL-audiobook-library](../goals/GOAL-audiobook-library.md)

## Acceptance Criteria

- Given an audiobook in the library, when I select it, then playback starts in the browser
- Given I stop playback and return later, when I select the same audiobook, then playback resumes from where I left off
- Given an audiobook with chapters, when playing, then I can navigate between chapters

## Derived Requirements

- [REQ-F-audiobook-playback](../requirements/REQ-F-audiobook-playback.md) — Browser playback with chapter navigation
- [REQ-F-playback-resume](../requirements/REQ-F-playback-resume.md) — Persist and resume playback position
