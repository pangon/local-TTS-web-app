# REQ-F-disk-space-preflight: Disk Space Check Before Synthesis

**Type**: Functional

**Status**: Draft

**Priority**: Must-have

**Source**: [US-create-audiobook](../user-stories/US-create-audiobook.md)

**Source stakeholder**: [STK-end-user](../stakeholders.md)

## Description

Before starting audiobook synthesis, the system shall estimate the required disk space for the output audio. If the estimated output size exceeds available disk space, synthesis shall not start and the UI shall display an error showing both the estimated space needed and the available space.

## Acceptance Criteria

- Given a user triggers synthesis, when the system estimates output size, then the estimate is calculated before any audio generation begins
- Given estimated output exceeds available disk space, when the preflight check runs, then synthesis does not start and the UI displays the estimated size and available space
- Given sufficient disk space is available, when the preflight check runs, then synthesis proceeds normally
