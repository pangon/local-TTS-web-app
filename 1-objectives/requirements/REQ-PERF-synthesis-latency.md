# REQ-PERF-synthesis-latency: Synthesis Latency Thresholds

**Type**: Performance

**Status**: Approved

**Priority**: Should-have

**Source**: [US-synthesize-text-input](../user-stories/US-synthesize-text-input.md), [US-create-audiobook](../user-stories/US-create-audiobook.md)

**Source stakeholder**: [STK-end-user](../stakeholders.md)

## Description

On minimum-spec hardware (NVIDIA GPU, 4 GB VRAM), text preview synthesis must deliver fast feedback for short text, and audiobook synthesis must maintain reasonable throughput relative to audio duration.

## Acceptance Criteria

- Given text input of ≤ 500 characters on minimum-spec hardware, when the user triggers preview synthesis, then audio playback begins within 30 seconds
- Given a full audiobook synthesis on minimum-spec hardware, when the job completes, then the real-time factor (synthesis time / audio duration) is ≤ 3.0
- Given any synthesis job, when estimated completion exceeds the applicable threshold, then the UI displays an estimated time remaining

## Related Constraints

- [CON-gpu-inference](../constraints/CON-gpu-inference.md) — GPU-only inference bounds achievable throughput

## Related Assumptions

- [ASM-user-has-nvidia-gpu](../assumptions/ASM-user-has-nvidia-gpu.md) — thresholds assume minimum 4 GB VRAM
