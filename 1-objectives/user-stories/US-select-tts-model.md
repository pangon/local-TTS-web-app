# US-select-tts-model: Select and Load a TTS Model

**As a** end user, **I want** to browse available HuggingFace TTS models and select one to use, **so that** I can choose the model that best suits my quality and performance needs.

**Status**: Approved

**Priority**: Must-have

**Source stakeholder**: [STK-end-user](../stakeholders.md)

**Related goal**: [GOAL-huggingface-models](../goals/GOAL-huggingface-models.md)

## Acceptance Criteria

- Given I open the model selection view, then I see a list of compatible open-weight TTS models available from HuggingFace
- Given a model that is not yet downloaded, when I select it, then the system downloads and caches it locally
- Given a model that is already cached, when I select it, then it loads without re-downloading
- Given a model is downloading, when I check the UI, then I see download progress
- Given insufficient disk space when I select a model to download, then the system shows an error with the required and available space instead of starting the download

## Derived Requirements

- [REQ-F-model-listing](../requirements/REQ-F-model-listing.md) — List available TTS models
- [REQ-F-model-download](../requirements/REQ-F-model-download.md) — Download, cache, and load models
