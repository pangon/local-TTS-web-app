# REQ-F-synthesis-progress: Synthesis Progress Indication

**Type**: Functional

**Status**: Approved

**Priority**: Must-have

**Source**: [US-create-audiobook](../user-stories/US-create-audiobook.md)

**Source stakeholder**: [STK-end-user](../stakeholders.md)

## Description

While an audiobook is being synthesized, the UI shall display the job's current status and a progress indicator, so the user knows what is happening and how far along the process is.

## Acceptance Criteria

- Given a synthesis job is running, when the user views the UI, then they see the job status (queued, processing, completed, or failed)
- Given a synthesis job is processing, when the user views the UI, then they see a progress indicator (percentage or step count)
- Given a synthesis job fails, when the user views the UI, then they see an error message describing what went wrong
