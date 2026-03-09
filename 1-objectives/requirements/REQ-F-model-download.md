# REQ-F-model-download: Download, Cache, and Load TTS Models

**Type**: Functional

**Status**: Approved

**Priority**: Must-have

**Source**: [US-select-tts-model](../user-stories/US-select-tts-model.md)

**Source stakeholder**: [STK-end-user](../stakeholders.md)

## Description

The system shall download and cache selected TTS models locally. Already-cached models shall load without re-downloading. The UI shall show download progress. Before starting a download, the system shall check available disk space and block with an error (showing required vs. available space) if insufficient.

## Acceptance Criteria

- Given the user selects a model that is not cached, when the download starts, then the UI displays download progress
- Given a model download completes, then the model is cached locally and available for use
- Given the user selects a model that is already cached, then it loads immediately without re-downloading
- Given insufficient disk space when the user selects a model to download, then the download does not start and the UI shows the required and available space

## Related Assumptions

- [ASM-internet-for-model-download](../assumptions/ASM-internet-for-model-download.md) — internet available for initial model download; synthesis is offline
