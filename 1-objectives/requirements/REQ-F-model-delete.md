# REQ-F-model-delete: Delete Cached Models

**Type**: Functional

**Status**: Approved

**Priority**: Should-have

**Source**: [US-manage-models](../user-stories/US-manage-models.md)

**Source stakeholder**: [STK-self-hoster](../stakeholders.md)

## Description

The system shall allow deletion of cached models that are not currently loaded. If the user attempts to delete the currently loaded model, the system shall warn and prevent deletion until a different model is loaded or no model is active.

## Acceptance Criteria

- Given a cached model that is not currently loaded, when the user chooses to delete it, then it is removed and disk space is freed
- Given the currently loaded model, when the user attempts to delete it, then the system warns and prevents deletion
- Given the user loads a different model, when they then delete the previously loaded model, then deletion proceeds normally
