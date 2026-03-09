# US-create-audiobook: Create Audiobook from Text File

**As a** end user, **I want** to upload a .txt file and have it converted into an audiobook, **so that** I can listen to text content without relying on a cloud service.

**Status**: Draft

**Priority**: Must-have

**Source stakeholder**: [STK-end-user](../stakeholders.md)

**Related goal**: [GOAL-local-tts-synthesis](../goals/GOAL-local-tts-synthesis.md), [GOAL-browser-ui](../goals/GOAL-browser-ui.md), [GOAL-audiobook-creation](../goals/GOAL-audiobook-creation.md)

## Acceptance Criteria

- Given a .txt file uploaded via the browser UI, when I trigger synthesis, then the full text is processed into audio entirely locally
- Given the source text contains chapter structure, when synthesis completes, then the system produces one MP3 file per chapter
- Given synthesis completes, then the audiobook is added to the library for later access
- Given a file is being synthesized, when I check the UI, then I see progress/status indication
- Given insufficient disk space when I trigger audiobook synthesis, then the system shows an error with the estimated space needed and available space instead of starting generation

## Derived Requirements

- [REQ-F-upload-text-file](../requirements/REQ-F-upload-text-file.md) — File upload acceptance
- [REQ-F-synthesize-audiobook](../requirements/REQ-F-synthesize-audiobook.md) — Local TTS synthesis
- [REQ-F-chapter-split-output](../requirements/REQ-F-chapter-split-output.md) — Chapter-based audio output
- [REQ-F-synthesis-progress](../requirements/REQ-F-synthesis-progress.md) — Progress indication
- [REQ-F-disk-space-preflight](../requirements/REQ-F-disk-space-preflight.md) — Disk space preflight check
