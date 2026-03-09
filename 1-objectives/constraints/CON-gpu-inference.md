# CON-gpu-inference: GPU-Only Inference

**Category**: Technical

**Status**: Active

**Source stakeholder**: [STK-self-hoster](../stakeholders.md)

## Description

All TTS model inference must run on a dedicated GPU. CPU-only inference is not a supported configuration.

## Rationale

TTS models require significant compute for real-time or near-real-time audio generation. GPU acceleration is essential for acceptable synthesis speed, especially for long-form content like audiobooks. Supporting CPU fallback would add complexity without meeting performance expectations.

## Impact

- Model selection is limited to those that fit in GPU VRAM.
- The deployment environment must include a compatible dedicated GPU.
- Framework and runtime choices must support GPU execution (e.g., CUDA-based inference).
- Users without a dedicated GPU cannot use the application.

## Related Artifacts

- [REQ-F-gpu-validation](../requirements/REQ-F-gpu-validation.md) — verifies GPU/CUDA availability on startup
- [REQ-F-synthesize-audiobook](../requirements/REQ-F-synthesize-audiobook.md) — all inference runs on GPU
- [REQ-PERF-synthesis-latency](../requirements/REQ-PERF-synthesis-latency.md) — latency thresholds assume GPU execution
