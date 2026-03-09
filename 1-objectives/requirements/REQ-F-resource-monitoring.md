# REQ-F-resource-monitoring: System Resource Usage Display

**Type**: Functional

**Status**: Approved

**Priority**: Should-have

**Source**: [US-monitor-jobs](../user-stories/US-monitor-jobs.md)

**Source stakeholder**: [STK-self-hoster](../stakeholders.md)

## Description

The system shall display current resource usage (CPU, memory, GPU utilization) and information about the currently loaded model in a monitoring view.

## Acceptance Criteria

- Given the backend is running, when the user opens the monitoring view, then current CPU, memory, and GPU utilization are displayed
- Given a model is loaded, when the user views the monitoring view, then the loaded model's name is shown
- Given no model is loaded, when the user views the monitoring view, then a clear indication of no active model is shown
