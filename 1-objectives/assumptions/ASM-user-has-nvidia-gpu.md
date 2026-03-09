# ASM-user-has-nvidia-gpu: Users Have an NVIDIA GPU with 4+ GB VRAM

**Category**: Environment

**Status**: Unverified

**Risk if wrong**: High — the application would be unusable without a compatible GPU; users without one cannot run TTS inference at all.

## Statement

Target users have a machine with a dedicated NVIDIA GPU that has at least 4 GB of VRAM and supports CUDA.

## Rationale

TTS models require GPU acceleration for acceptable performance. 4 GB VRAM is the minimum to run small-to-medium open-weight TTS models (e.g., Piper, smaller Coqui variants). NVIDIA GPUs with CUDA are the most widely supported platform for AI inference.

## Verification Plan

Test during development with a 4 GB VRAM card (e.g., GTX 1650) to confirm that at least one target TTS model runs within memory limits and produces audio at acceptable speed.

## Related Artifacts

- [CON-gpu-inference](../constraints/CON-gpu-inference.md)
- [CON-nvidia-gpu](../constraints/CON-nvidia-gpu.md)
- [GOAL-local-tts-synthesis](../goals/GOAL-local-tts-synthesis.md)
- [GOAL-huggingface-models](../goals/GOAL-huggingface-models.md)
