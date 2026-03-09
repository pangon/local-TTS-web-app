# REQ-F-model-cache-view: View Cached Models and Disk Usage

**Type**: Functional

**Status**: Approved

**Priority**: Should-have

**Source**: [US-manage-models](../user-stories/US-manage-models.md)

**Source stakeholder**: [STK-self-hoster](../stakeholders.md)

## Description

The system shall display a list of cached models with their name and disk size, so the self-hoster can assess storage consumption.

## Acceptance Criteria

- Given one or more models are cached, when the user opens the model management view, then each cached model's name and disk size are displayed
- Given no models are cached, when the user opens the model management view, then an empty state message is shown
