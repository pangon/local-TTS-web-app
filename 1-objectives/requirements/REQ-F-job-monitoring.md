# REQ-F-job-monitoring: TTS Job Status and Error Details

**Type**: Functional

**Status**: Draft

**Priority**: Should-have

**Source**: [US-monitor-jobs](../user-stories/US-monitor-jobs.md)

**Source stakeholder**: [STK-self-hoster](../stakeholders.md)

## Description

The system shall display a list of TTS jobs with their current status (queued, processing, completed, failed) and progress. For failed jobs, error details and relevant log output are shown.

## Acceptance Criteria

- Given one or more TTS jobs exist, when the user opens the monitoring view, then each job's status and progress are visible
- Given a job has failed, when the user views it in the monitoring view, then error details and relevant log output are shown
- Given no jobs exist, when the user opens the monitoring view, then an empty state message is displayed
