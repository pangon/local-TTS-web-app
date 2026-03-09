# REQ-F-model-listing: List Available TTS Models

**Type**: Functional

**Status**: Draft

**Priority**: Must-have

**Source**: [US-select-tts-model](../user-stories/US-select-tts-model.md)

**Source stakeholder**: [STK-end-user](../stakeholders.md)

## Description

The system shall display a list of compatible open-weight TTS models from HuggingFace, indicating which models are already cached locally.

## Acceptance Criteria

- Given the user opens the model selection view, then a list of compatible TTS models is displayed
- Given a model in the list that is cached locally, then it is visually distinguished from models that require downloading
- Given models are listed, then each entry shows the model name and its cache status (cached or not cached)

## Related Assumptions

- [ASM-huggingface-models-available](../assumptions/ASM-huggingface-models-available.md) — assumes suitable open-weight TTS models exist on HuggingFace
