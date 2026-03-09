# CON-nvidia-gpu: NVIDIA GPU Required

**Category**: Technical

**Status**: Active

**Source stakeholder**: [STK-self-hoster](../stakeholders.md)

## Description

Only NVIDIA GPUs with CUDA support are targeted. AMD (ROCm) and Apple Silicon (MPS) GPU acceleration are out of scope for the initial version.

## Rationale

NVIDIA CUDA has the broadest ecosystem support for AI/ML inference frameworks and model compatibility. Targeting a single GPU vendor simplifies development, testing, and dependency management. AMD and Apple Silicon support may be revisited in future iterations.

## Impact

- All GPU-related dependencies and runtime configuration target CUDA.
- macOS is out of scope (see CON-cross-platform).
- Testing requires NVIDIA hardware.
