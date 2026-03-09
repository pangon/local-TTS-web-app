# REQ-F-gpu-validation: GPU and VRAM Preflight Check

**Type**: Functional

**Status**: Draft

**Priority**: Must-have

**Source**: [GOAL-local-tts-synthesis](../goals/GOAL-local-tts-synthesis.md)

**Source stakeholder**: [STK-self-hoster](../stakeholders.md)

## Description

On startup, the system shall verify that a compatible NVIDIA GPU with CUDA support is available. Before loading a TTS model, the system shall verify that sufficient VRAM is available. If either check fails, the system shall display a clear error message describing the problem and what is needed.

## Acceptance Criteria

- Given the application starts, when no NVIDIA GPU with CUDA support is detected, then the system displays a clear error identifying the issue instead of failing silently
- Given the user selects a model to load, when the model's VRAM requirement exceeds available VRAM, then the system displays an error showing required and available VRAM instead of attempting to load
- Given a compatible GPU with sufficient VRAM, then startup and model loading proceed normally

## Related Constraints

- [CON-gpu-inference](../constraints/CON-gpu-inference.md) — all TTS inference must run on a dedicated GPU
- [CON-nvidia-gpu](../constraints/CON-nvidia-gpu.md) — only NVIDIA GPUs (CUDA) are supported

## Related Assumptions

- [ASM-user-has-nvidia-gpu](../assumptions/ASM-user-has-nvidia-gpu.md) — users have an NVIDIA GPU with at least 4 GB VRAM
