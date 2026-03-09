# ASM-internet-for-model-download: Internet Available for Initial Model Download

**Category**: Environment

**Status**: Verified

**Risk if wrong**: Low — users could sideload model files manually via file system; the application would still function once models are cached locally.

## Statement

Users have internet connectivity when first downloading a TTS model. After the initial download, models are cached locally and synthesis operates fully offline.

## Rationale

GOAL-huggingface-models requires on-demand model downloads from HuggingFace. The core privacy promise (GOAL-local-tts-synthesis) applies to the synthesis step, not to model acquisition. Requiring internet only for the initial download is a reasonable trade-off.

## Verification Plan

Confirmed by design: the model download and caching flow will be built as a distinct step from inference. Verify that the application handles offline scenarios gracefully (e.g., shows cached models only, clear error if no models available).

## Related Artifacts

- [GOAL-huggingface-models](../goals/GOAL-huggingface-models.md)
- [GOAL-local-tts-synthesis](../goals/GOAL-local-tts-synthesis.md)
