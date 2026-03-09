# REQ-F-upload-text-file: File Upload for Audiobook Synthesis

**Type**: Functional

**Status**: Draft

**Priority**: Must-have

**Source**: [US-create-audiobook](../user-stories/US-create-audiobook.md)

**Source stakeholder**: [STK-end-user](../stakeholders.md)

## Description

The system shall accept `.txt` file uploads (UTF-8 encoded, up to 2 MB) through the browser UI as input for audiobook synthesis.

## Acceptance Criteria

- Given a user on the audiobook creation page, when they select a valid `.txt` file (UTF-8, ≤ 2 MB), then the file is accepted and ready for synthesis
- Given a user uploads a file exceeding 2 MB, when the upload is attempted, then the system rejects it with a clear error message stating the size limit
- Given a user uploads a non-`.txt` file, when the upload is attempted, then the system rejects it with a clear error message stating the accepted format

## Related Assumptions

- [ASM-text-file-format](../assumptions/ASM-text-file-format.md) — assumes users provide UTF-8 `.txt` files up to ~2 MB
