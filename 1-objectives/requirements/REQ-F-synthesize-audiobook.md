# REQ-F-synthesize-audiobook: Local Text-to-Speech Synthesis

**Type**: Functional

**Status**: Draft

**Priority**: Must-have

**Source**: [US-create-audiobook](../user-stories/US-create-audiobook.md)

**Source stakeholder**: [STK-end-user](../stakeholders.md)

## Description

The system shall convert the full uploaded text into MP3 audio using the currently selected TTS model, with all inference running locally on the GPU. No data shall be sent to external services during synthesis.

## Acceptance Criteria

- Given a valid uploaded `.txt` file and a selected TTS model, when the user triggers synthesis, then the system produces MP3 audio covering the entire text content
- Given synthesis is triggered, then all TTS inference executes locally on the GPU with zero external API calls
- Given synthesis completes successfully, then the resulting audiobook is automatically added to the library for later access

## Related Constraints

- [CON-gpu-inference](../constraints/CON-gpu-inference.md) — all TTS inference must run on a dedicated GPU
- [CON-nvidia-gpu](../constraints/CON-nvidia-gpu.md) — only NVIDIA GPUs (CUDA) are supported
