# REQ-F-delete-audiobook: Delete Audiobook with Confirmation

**Type**: Functional

**Status**: Approved

**Priority**: Must-have

**Source**: [US-delete-audiobook](../user-stories/US-delete-audiobook.md)

**Source stakeholder**: [STK-end-user](../stakeholders.md)

## Description

The system shall delete an audiobook and all its associated audio files from storage. A confirmation prompt shall be shown before deletion proceeds.

## Acceptance Criteria

- Given the user requests deletion of an audiobook, then a confirmation prompt is shown before any files are removed
- Given the user confirms deletion, then the audiobook entry and all associated audio files are removed from storage
- Given the user cancels deletion, then the audiobook remains unchanged
