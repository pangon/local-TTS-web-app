# REQ-F-chapter-split-output: Chapter-Based Audio Output

**Type**: Functional

**Status**: Approved

**Priority**: Must-have

**Source**: [US-create-audiobook](../user-stories/US-create-audiobook.md)

**Source stakeholder**: [STK-end-user](../stakeholders.md)

## Description

When the source text contains chapter structure, the system shall produce one MP3 file per detected chapter. When no chapter structure is detected, a single MP3 file shall be produced for the entire text. The specific chapter detection patterns (heading formats, delimiters) are deferred to the design phase and will be refined through testing during implementation.

## Acceptance Criteria

- Given an uploaded text with recognizable chapter markers, when synthesis completes, then the system produces one MP3 file per chapter
- Given an uploaded text with no recognizable chapter markers, when synthesis completes, then the system produces a single MP3 file
- Given chapter-split output, then each chapter file is labeled with its chapter number or title for identification
