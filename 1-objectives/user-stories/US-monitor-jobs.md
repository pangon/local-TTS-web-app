# US-monitor-jobs: Monitor Processing Jobs

**As a** self-hoster, **I want** to view the status of ongoing TTS jobs and system resource usage, **so that** I can verify the backend is healthy and diagnose issues.

**Status**: Draft

**Priority**: Should-have

**Source stakeholder**: [STK-self-hoster](../stakeholders.md)

**Related goal**: [GOAL-backend-monitoring](../goals/GOAL-backend-monitoring.md)

## Acceptance Criteria

- Given one or more TTS jobs are running, when I open the monitoring view, then I see each job's status and progress
- Given the backend is running, when I open the monitoring view, then I see current resource usage (CPU, memory, GPU if applicable) and loaded model info
- Given a job fails, when I check the monitoring view, then I see the error details and relevant log output

## Derived Requirements

- [REQ-F-job-monitoring](../requirements/REQ-F-job-monitoring.md) — TTS job status and error details
- [REQ-F-resource-monitoring](../requirements/REQ-F-resource-monitoring.md) — System resource usage display
