# ASM-huggingface-models-available: Suitable Open-Weight TTS Models Exist on HuggingFace

**Category**: Technology

**Status**: Unverified

**Risk if wrong**: High — GOAL-huggingface-models depends entirely on this; without suitable models, the core TTS feature cannot function as designed.

## Statement

HuggingFace hosts open-weight TTS models that produce acceptable audio quality, fit within 4 GB VRAM, and can be loaded on-demand via standard tooling (e.g., transformers, huggingface_hub).

## Rationale

Several open-weight TTS models are currently available on HuggingFace, including Coqui XTTS, Bark, Piper, and others. The HuggingFace ecosystem provides standardized model hosting, versioning, and download APIs.

## Verification Plan

Survey HuggingFace for TTS models that meet the following criteria: (1) open-weight license, (2) fit in 4 GB VRAM, (3) produce natural-sounding speech, (4) support English at minimum. Document at least two viable candidates with benchmark results.

## Related Artifacts

- [GOAL-huggingface-models](../goals/GOAL-huggingface-models.md)
- [GOAL-audio-quality](../goals/GOAL-audio-quality.md)
- [ASM-user-has-nvidia-gpu](ASM-user-has-nvidia-gpu.md)
