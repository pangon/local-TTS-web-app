# REQ-F-performance-logging: Record Synthesis Performance Metrics

**Type**: Functional

**Status**: Approved

**Priority**: Should-have

**Source**: [US-evaluate-local-ai](../user-stories/US-evaluate-local-ai.md)

**Source stakeholder**: [STK-developer](../stakeholders.md)

## Description

The system shall record performance metrics (latency, resource usage) for each synthesis run, accessible for review.

## Acceptance Criteria

- Given a synthesis run completes, then performance metrics (latency, resource usage) are recorded and retrievable
- Given recorded metrics, when the user accesses them, then they are presented in a readable format (e.g., log file or UI view)
