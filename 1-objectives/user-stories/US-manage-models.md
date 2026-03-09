# US-manage-models: Manage Cached TTS Models

**As a** self-hoster, **I want** to view cached models and their disk usage and delete models I no longer need, **so that** I can control storage consumption.

**Status**: Approved

**Priority**: Should-have

**Source stakeholder**: [STK-self-hoster](../stakeholders.md)

**Related goal**: [GOAL-huggingface-models](../goals/GOAL-huggingface-models.md)

## Acceptance Criteria

- Given one or more models have been downloaded, when I open the model management view, then I see each cached model with its name and disk size
- Given a cached model that is not currently loaded, when I choose to delete it, then it is removed and the disk space is freed
- Given I attempt to delete the currently loaded model, then the system warns me and prevents deletion until a different model is loaded or no model is active

## Derived Requirements

- [REQ-F-model-cache-view](../requirements/REQ-F-model-cache-view.md) — View cached models and disk usage
- [REQ-F-model-delete](../requirements/REQ-F-model-delete.md) — Delete cached models
